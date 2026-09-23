"""
Regras de negocio PURAS da biblioteca (sem dependencia de Django).

Ficam separadas dos models/views para serem simples de ler e de testar.
"""
from datetime import date, timedelta
from decimal import Decimal

PRAZO_EMPRESTIMO_DIAS = 14
MULTA_POR_DIA = Decimal("0.50")
LIMITE_EMPRESTIMOS_ABERTOS = 3


def calcular_prazo(data_emprestimo: date) -> date:
    """Data limite de devolucao a partir da data do emprestimo."""
    return data_emprestimo + timedelta(days=PRAZO_EMPRESTIMO_DIAS)


def dias_atraso(data_prevista: date, data_referencia: date) -> int:
    """Dias corridos de atraso (0 se devolvido/consultado dentro do prazo)."""
    return max((data_referencia - data_prevista).days, 0)


def calcular_multa(data_prevista: date, data_referencia: date) -> Decimal:
    """Multa = dias de atraso x valor diario. A data limite em si nao gera multa."""
    valor = MULTA_POR_DIA * dias_atraso(data_prevista, data_referencia)
    return valor.quantize(Decimal("0.01"))


def pode_retirar(posicao_na_fila: int | None, tamanho_fila: int, disponiveis: int) -> bool:
    """
    Decide se um membro pode retirar um exemplar de um livro com fila de reserva.

    - posicao_na_fila: posicao (1, 2, ...) do membro na fila, ou None se ele nao reservou.
    - tamanho_fila: quantas reservas ativas existem para o livro.
    - disponiveis: exemplares fisicos livres agora.

    Os exemplares livres sao "guardados" para os primeiros da fila. Quem nao
    reservou so retira se sobrar exemplar depois de atender toda a fila.
    """
    if disponiveis <= 0:
        return False
    if tamanho_fila == 0:
        return True
    if posicao_na_fila is not None:
        return posicao_na_fila <= disponiveis
    return tamanho_fila < disponiveis
