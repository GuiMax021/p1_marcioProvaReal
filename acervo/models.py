from django.db import models
from django.db.models import Q
from django.utils import timezone

from . import regras


class Categoria(models.Model):
    """Categoria da Classificacao Decimal de Dewey (000 a 900)."""

    codigo = models.CharField("código CDD", max_length=3, unique=True)
    nome = models.CharField(max_length=80)

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class Autor(models.Model):
    nome = models.CharField(max_length=150)

    class Meta:
        ordering = ["nome"]
        verbose_name_plural = "autores"

    def __str__(self):
        return self.nome


class Livro(models.Model):
    titulo = models.CharField("título", max_length=200)
    autores = models.ManyToManyField(Autor, related_name="livros")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="livros")
    ano = models.PositiveSmallIntegerField()
    editora = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["titulo"]

    def __str__(self):
        return self.titulo

    @property
    def autores_texto(self):
        return ", ".join(a.nome for a in self.autores.all())

    @property
    def total_exemplares(self):
        return self.exemplares.count()

    @property
    def disponiveis(self):
        return Exemplar.objects.disponiveis().filter(livro=self).count()

    @property
    def fila_reservas(self):
        return self.reservas.filter(status=Reserva.Status.ATIVA).select_related("membro")


class ExemplarQuerySet(models.QuerySet):
    def disponiveis(self):
        """Exemplares fisicos sem emprestimo em aberto."""
        return self.filter(tipo=Exemplar.Tipo.FISICO).exclude(
            emprestimos__data_devolucao__isnull=True
        )


class Exemplar(models.Model):
    class Tipo(models.TextChoices):
        FISICO = "FISICO", "Físico"
        DIGITAL = "DIGITAL", "Digital"

    livro = models.ForeignKey(Livro, on_delete=models.CASCADE, related_name="exemplares")
    codigo = models.CharField("código/tombo", max_length=20, unique=True)
    tipo = models.CharField(max_length=7, choices=Tipo.choices, default=Tipo.FISICO)
    localizacao = models.CharField("localização", max_length=60)

    objects = ExemplarQuerySet.as_manager()

    class Meta:
        ordering = ["codigo"]
        verbose_name_plural = "exemplares"

    def __str__(self):
        return f"{self.codigo} - {self.livro.titulo}"

    @property
    def emprestado(self):
        return self.emprestimos.filter(data_devolucao__isnull=True).exists()

    @property
    def situacao(self):
        if self.tipo == self.Tipo.DIGITAL:
            return "Acesso digital"
        return "Emprestado" if self.emprestado else "Disponível"


class Membro(models.Model):
    nome = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=20, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def emprestimos_abertos(self):
        return self.emprestimos.filter(data_devolucao__isnull=True)

    @property
    def multa_pendente(self):
        """Soma das multas ja apuradas e nao pagas."""
        total = self.emprestimos.filter(multa__gt=0, multa_paga=False).aggregate(
            t=models.Sum("multa")
        )["t"]
        return total or 0


class Emprestimo(models.Model):
    exemplar = models.ForeignKey(Exemplar, on_delete=models.PROTECT, related_name="emprestimos")
    membro = models.ForeignKey(Membro, on_delete=models.PROTECT, related_name="emprestimos")
    data_emprestimo = models.DateField(default=timezone.localdate)
    data_prevista = models.DateField("devolução prevista")
    data_devolucao = models.DateField("devolvido em", null=True, blank=True)
    multa = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    multa_paga = models.BooleanField(default=False)

    class Meta:
        ordering = ["-data_emprestimo", "-id"]
        constraints = [
            # Garante no banco: um exemplar nunca tem dois emprestimos abertos.
            models.UniqueConstraint(
                fields=["exemplar"],
                condition=Q(data_devolucao__isnull=True),
                name="um_emprestimo_aberto_por_exemplar",
            )
        ]

    def __str__(self):
        return f"{self.exemplar.codigo} -> {self.membro.nome}"

    @property
    def aberto(self):
        return self.data_devolucao is None

    @property
    def dias_atraso(self):
        ref = self.data_devolucao or timezone.localdate()
        return regras.dias_atraso(self.data_prevista, ref)

    @property
    def em_atraso(self):
        return self.aberto and self.dias_atraso > 0

    @property
    def multa_atual(self):
        """Multa devida: a gravada (devolvido) ou a projetada ate hoje (aberto)."""
        if self.aberto:
            return regras.calcular_multa(self.data_prevista, timezone.localdate())
        return self.multa


class Reserva(models.Model):
    class Status(models.TextChoices):
        ATIVA = "ATIVA", "Ativa (na fila)"
        ATENDIDA = "ATENDIDA", "Atendida"
        CANCELADA = "CANCELADA", "Cancelada"

    livro = models.ForeignKey(Livro, on_delete=models.CASCADE, related_name="reservas")
    membro = models.ForeignKey(Membro, on_delete=models.CASCADE, related_name="reservas")
    criada_em = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ATIVA)

    class Meta:
        ordering = ["criada_em", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["livro", "membro"],
                condition=Q(status="ATIVA"),
                name="uma_reserva_ativa_por_membro_e_livro",
            )
        ]

    def __str__(self):
        return f"{self.livro.titulo} ({self.membro.nome})"

    @property
    def posicao_na_fila(self):
        if self.status != self.Status.ATIVA:
            return None
        ids = list(
            Reserva.objects.filter(livro=self.livro_id, status=self.Status.ATIVA)
            .order_by("criada_em", "id")
            .values_list("id", flat=True)
        )
        return ids.index(self.id) + 1
