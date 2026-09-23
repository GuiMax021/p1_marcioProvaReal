"""
Casos de uso da biblioteca. Toda operacao que altera estado passa por aqui,
para que views, admin, comandos e futura API (P2) compartilhem as mesmas regras.
"""
from django.db import transaction
from django.utils import timezone

from . import regras
from .models import Emprestimo, Exemplar, Reserva


class RegraDeNegocioError(Exception):
    """Violacao de regra de negocio; a mensagem e exibivel ao usuario."""


def _disponiveis_do_livro(livro):
    return Exemplar.objects.disponiveis().filter(livro=livro).count()


@transaction.atomic
def emprestar(exemplar, membro, hoje=None):
    hoje = hoje or timezone.localdate()
    exemplar = Exemplar.objects.select_for_update().select_related("livro").get(pk=exemplar.pk)
    livro = exemplar.livro

    if not membro.ativo:
        raise RegraDeNegocioError("Membro inativo não pode fazer empréstimos.")
    if exemplar.tipo != Exemplar.Tipo.FISICO:
        raise RegraDeNegocioError("Exemplares digitais não são emprestados (acesso pelo repositório).")
    if exemplar.emprestimos.filter(data_devolucao__isnull=True).exists():
        raise RegraDeNegocioError("Este exemplar já está emprestado.")

    abertos = membro.emprestimos_abertos
    if abertos.count() >= regras.LIMITE_EMPRESTIMOS_ABERTOS:
        raise RegraDeNegocioError(
            f"Limite de {regras.LIMITE_EMPRESTIMOS_ABERTOS} empréstimos simultâneos atingido."
        )
    if abertos.filter(exemplar__livro=livro).exists():
        raise RegraDeNegocioError("O membro já está com um exemplar deste livro.")
    if any(e.data_prevista < hoje for e in abertos):
        raise RegraDeNegocioError("O membro possui empréstimo em atraso. Devolva antes de retirar outro.")
    if membro.multa_pendente > 0:
        raise RegraDeNegocioError(
            f"O membro possui multa pendente de R$ {membro.multa_pendente}. Quite antes de retirar."
        )

    # Fila de reserva: exemplares livres sao guardados para os primeiros da fila.
    fila_ids = list(
        Reserva.objects.filter(livro=livro, status=Reserva.Status.ATIVA)
        .order_by("criada_em", "id")
        .values_list("membro_id", flat=True)
    )
    posicao = fila_ids.index(membro.pk) + 1 if membro.pk in fila_ids else None
    if not regras.pode_retirar(posicao, len(fila_ids), _disponiveis_do_livro(livro)):
        if posicao:
            raise RegraDeNegocioError(f"Aguarde sua vez: você é o {posicao}º da fila deste livro.")
        raise RegraDeNegocioError("Este livro tem fila de reserva; apenas quem reservou pode retirá-lo.")

    emprestimo = Emprestimo.objects.create(
        exemplar=exemplar,
        membro=membro,
        data_emprestimo=hoje,
        data_prevista=regras.calcular_prazo(hoje),
    )
    if posicao:
        Reserva.objects.filter(
            livro=livro, membro=membro, status=Reserva.Status.ATIVA
        ).update(status=Reserva.Status.ATENDIDA)
    return emprestimo


@transaction.atomic
def devolver(emprestimo, hoje=None):
    hoje = hoje or timezone.localdate()
    if not emprestimo.aberto:
        raise RegraDeNegocioError("Este empréstimo já foi devolvido.")
    emprestimo.data_devolucao = hoje
    emprestimo.multa = regras.calcular_multa(emprestimo.data_prevista, hoje)
    emprestimo.save(update_fields=["data_devolucao", "multa"])
    return emprestimo


def pagar_multa(emprestimo):
    if emprestimo.aberto:
        raise RegraDeNegocioError("Devolva o exemplar antes de quitar a multa.")
    if emprestimo.multa <= 0:
        raise RegraDeNegocioError("Este empréstimo não possui multa.")
    emprestimo.multa_paga = True
    emprestimo.save(update_fields=["multa_paga"])
    return emprestimo


@transaction.atomic
def reservar(livro, membro):
    if not membro.ativo:
        raise RegraDeNegocioError("Membro inativo não pode reservar.")
    if not livro.exemplares.filter(tipo=Exemplar.Tipo.FISICO).exists():
        raise RegraDeNegocioError("Este livro não possui exemplar físico para reservar.")
    if membro.emprestimos_abertos.filter(exemplar__livro=livro).exists():
        raise RegraDeNegocioError("O membro já está com um exemplar deste livro.")
    if Reserva.objects.filter(livro=livro, membro=membro, status=Reserva.Status.ATIVA).exists():
        raise RegraDeNegocioError("O membro já está na fila deste livro.")
    return Reserva.objects.create(livro=livro, membro=membro)


def cancelar_reserva(reserva):
    if reserva.status != Reserva.Status.ATIVA:
        raise RegraDeNegocioError("Apenas reservas ativas podem ser canceladas.")
    reserva.status = Reserva.Status.CANCELADA
    reserva.save(update_fields=["status"])
    return reserva
