from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView, DeleteView, DetailView, FormView, ListView, TemplateView, UpdateView,
)

from . import services
from .forms import EmprestimoForm, LivroForm, ReservaForm
from .models import Autor, Categoria, Emprestimo, Exemplar, Livro, Membro, Reserva
from .services import RegraDeNegocioError


def querystring(request):
    """Parametros da URL sem 'page', para manter filtros ao paginar."""
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


# ---------- Home ----------
class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "acervo/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoje = timezone.localdate()
        abertos = Emprestimo.objects.filter(data_devolucao__isnull=True)
        ctx.update(
            total_livros=Livro.objects.count(),
            total_exemplares=Exemplar.objects.count(),
            total_membros=Membro.objects.filter(ativo=True).count(),
            emprestimos_abertos=abertos.count(),
            emprestimos_atrasados=abertos.filter(data_prevista__lt=hoje).count(),
            reservas_ativas=Reserva.objects.filter(status=Reserva.Status.ATIVA).count(),
        )
        return ctx


# ---------- CRUD generico ----------
class ListaBase(LoginRequiredMixin, ListView):
    template_name = "acervo/lista.html"
    paginate_by = 20
    titulo = ""
    colunas = []
    prefixo = ""
    campos_busca = ()

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q and self.campos_busca:
            filtro = Q()
            for campo in self.campos_busca:
                filtro |= Q(**{f"{campo}__icontains": q})
            qs = qs.filter(filtro).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            titulo=self.titulo, colunas=self.colunas, prefixo=self.prefixo,
            q=self.request.GET.get("q", ""), pode_buscar=bool(self.campos_busca),
            params=querystring(self.request),
        )
        return ctx


class FormBase(LoginRequiredMixin, SuccessMessageMixin):
    template_name = "acervo/form.html"
    prefixo = ""
    titulo = ""

    def get_success_url(self):
        return reverse(f"{self.prefixo}_lista")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(titulo=self.titulo, prefixo=self.prefixo)
        return ctx


class ExcluirBase(LoginRequiredMixin, DeleteView):
    template_name = "acervo/confirmar_exclusao.html"
    prefixo = ""

    def get_success_url(self):
        return reverse(f"{self.prefixo}_lista")

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "Não é possível excluir: existem registros vinculados a este item.")
            return redirect(self.get_success_url())
        messages.success(self.request, "Registro excluído.")
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["prefixo"] = self.prefixo
        return ctx


def crud(modelo, prefixo, titulo, colunas, campos=None, busca=(), form_class=None):
    nome = modelo.__name__
    lista = type(f"{nome}Lista", (ListaBase,), dict(
        model=modelo, prefixo=prefixo, titulo=titulo, colunas=colunas, campos_busca=busca))
    # Usa um ModelForm proprio quando informado; senao, gera um a partir de 'campos'.
    config_form = {"form_class": form_class} if form_class else {"fields": campos}
    criar = type(f"{nome}Criar", (FormBase, CreateView), dict(
        model=modelo, prefixo=prefixo, titulo=f"Novo cadastro: {titulo}",
        success_message="Registro criado com sucesso.", **config_form))
    editar = type(f"{nome}Editar", (FormBase, UpdateView), dict(
        model=modelo, prefixo=prefixo, titulo=f"Editar: {titulo}",
        success_message="Registro atualizado com sucesso.", **config_form))
    excluir = type(f"{nome}Excluir", (ExcluirBase,), dict(model=modelo, prefixo=prefixo))
    return lista, criar, editar, excluir


CategoriaLista, CategoriaCriar, CategoriaEditar, CategoriaExcluir = crud(
    Categoria, "categoria", "Categorias (CDD)",
    [("Código", "codigo"), ("Nome", "nome")], ["codigo", "nome"], busca=("codigo", "nome"))

AutorLista, AutorCriar, AutorEditar, AutorExcluir = crud(
    Autor, "autor", "Autores", [("Nome", "nome")], ["nome"], busca=("nome",))

_, LivroCriar, LivroEditar, LivroExcluir = crud(
    Livro, "livro", "Livros",
    [("Título", "titulo"), ("Autores", "autores_texto"), ("Categoria", "categoria"),
     ("Ano", "ano"), ("Disponíveis", "disponiveis")],
    busca=("titulo", "autores__nome"), form_class=LivroForm)

ExemplarLista, ExemplarCriar, ExemplarEditar, ExemplarExcluir = crud(
    Exemplar, "exemplar", "Exemplares",
    [("Código", "codigo"), ("Livro", "livro"), ("Tipo", "tipo"),
     ("Localização", "localizacao"), ("Situação", "situacao")],
    ["livro", "codigo", "tipo", "localizacao"], busca=("codigo", "livro__titulo"))

MembroLista, MembroCriar, MembroEditar, MembroExcluir = crud(
    Membro, "membro", "Membros",
    [("Nome", "nome"), ("E-mail", "email"), ("Telefone", "telefone"), ("Ativo", "ativo")],
    ["nome", "email", "telefone", "ativo"], busca=("nome", "email"))


class LivroLista(LoginRequiredMixin, ListView):
    """
    Listagem principal com busca e filtros (Feature 1).

    Parametros da URL (todos opcionais e combinaveis):
      ?q=texto          busca por titulo OU nome do autor (icontains)
      ?status=...       disponivel | emprestado
      ?categoria=<id>   categoria CDD
    """
    model = Livro
    template_name = "acervo/livro_lista.html"
    paginate_by = 20

    def get_queryset(self):
        qs = Livro.objects.select_related("categoria").prefetch_related("autores")

        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        categoria = self.request.GET.get("categoria", "")

        if q:
            # Q() combina titulo OU autor numa unica consulta
            qs = qs.filter(Q(titulo__icontains=q) | Q(autores__nome__icontains=q))

        if categoria.isdigit():
            qs = qs.filter(categoria_id=int(categoria))

        livres = Exemplar.objects.disponiveis().values_list("livro_id", flat=True)
        if status == "disponivel":
            qs = qs.filter(pk__in=livres)
        elif status == "emprestado":
            # tem exemplar fisico, mas nenhum esta livre
            qs = qs.filter(exemplares__tipo=Exemplar.Tipo.FISICO).exclude(pk__in=livres)

        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            categorias=Categoria.objects.all(),
            q=self.request.GET.get("q", ""),
            status=self.request.GET.get("status", ""),
            categoria=self.request.GET.get("categoria", ""),
            params=querystring(self.request),
        )
        return ctx


class LivroDetalhe(LoginRequiredMixin, DetailView):
    model = Livro
    template_name = "acervo/livro_detalhe.html"


# ---------- Emprestimos ----------
class EmprestimoLista(LoginRequiredMixin, ListView):
    model = Emprestimo
    template_name = "acervo/emprestimos.html"
    paginate_by = 20

    def get_queryset(self):
        qs = Emprestimo.objects.select_related("exemplar__livro", "membro")
        self.filtro = self.request.GET.get("status", "abertos")
        hoje = timezone.localdate()
        if self.filtro == "abertos":
            qs = qs.filter(data_devolucao__isnull=True)
        elif self.filtro == "atrasados":
            qs = qs.filter(data_devolucao__isnull=True, data_prevista__lt=hoje)
        elif self.filtro == "multas":
            qs = qs.filter(multa__gt=0, multa_paga=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filtro"] = self.filtro
        ctx["params"] = querystring(self.request)
        return ctx


class EmprestimoCriar(LoginRequiredMixin, FormView):
    form_class = EmprestimoForm
    template_name = "acervo/form.html"
    success_url = reverse_lazy("emprestimo_lista")
    extra_context = {"titulo": "Novo empréstimo", "prefixo": "emprestimo", "rotulo": "Emprestar"}

    def form_valid(self, form):
        try:
            emp = services.emprestar(form.cleaned_data["exemplar"], form.cleaned_data["membro"])
        except RegraDeNegocioError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, f"Empréstimo registrado. Devolução até {emp.data_prevista:%d/%m/%Y}.")
        return super().form_valid(form)


class _AcaoPost(LoginRequiredMixin, View):
    """Base para acoes POST sobre um objeto (devolver, pagar, cancelar)."""
    modelo = None
    destino = ""

    def executar(self, obj):
        raise NotImplementedError

    def post(self, request, pk):
        obj = get_object_or_404(self.modelo, pk=pk)
        try:
            messages.success(request, self.executar(obj))
        except RegraDeNegocioError as e:
            messages.error(request, str(e))
        return redirect(self.destino)


class EmprestimoDevolver(_AcaoPost):
    modelo = Emprestimo
    destino = "emprestimo_lista"

    def executar(self, emp):
        services.devolver(emp)
        if emp.multa > 0:
            return f"Devolvido com atraso de {emp.dias_atraso} dia(s). Multa: R$ {emp.multa}."
        return "Devolução registrada."


class EmprestimoPagarMulta(_AcaoPost):
    modelo = Emprestimo
    destino = "emprestimo_lista"

    def executar(self, emp):
        services.pagar_multa(emp)
        return "Multa quitada."


# ---------- Reservas ----------
class ReservaLista(LoginRequiredMixin, ListView):
    model = Reserva
    template_name = "acervo/reservas.html"
    paginate_by = 20

    def get_queryset(self):
        qs = Reserva.objects.select_related("livro", "membro")
        if self.request.GET.get("status", "ativas") == "ativas":
            qs = qs.filter(status=Reserva.Status.ATIVA)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["params"] = querystring(self.request)
        return ctx


class ReservaCriar(LoginRequiredMixin, FormView):
    form_class = ReservaForm
    template_name = "acervo/form.html"
    success_url = reverse_lazy("reserva_lista")
    extra_context = {"titulo": "Nova reserva", "prefixo": "reserva", "rotulo": "Reservar"}

    def get_initial(self):
        livro = self.request.GET.get("livro")
        return {"livro": livro} if livro else {}

    def form_valid(self, form):
        try:
            r = services.reservar(form.cleaned_data["livro"], form.cleaned_data["membro"])
        except RegraDeNegocioError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, f"Reserva criada: {r.posicao_na_fila}º na fila.")
        return super().form_valid(form)


class ReservaCancelar(_AcaoPost):
    modelo = Reserva
    destino = "reserva_lista"

    def executar(self, reserva):
        services.cancelar_reserva(reserva)
        return "Reserva cancelada."
