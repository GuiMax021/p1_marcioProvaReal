"""Testes das regras puras (rodam sem banco): python -m unittest acervo.tests_regras"""
import unittest
from datetime import date
from decimal import Decimal

from acervo import regras


class PrazoEMultaTests(unittest.TestCase):
    def test_prazo_e_14_dias(self):
        self.assertEqual(regras.calcular_prazo(date(2026, 1, 1)), date(2026, 1, 15))

    def test_sem_multa_no_prazo_e_no_dia_limite(self):
        prevista = date(2026, 1, 15)
        self.assertEqual(regras.calcular_multa(prevista, date(2026, 1, 10)), Decimal("0.00"))
        self.assertEqual(regras.calcular_multa(prevista, prevista), Decimal("0.00"))

    def test_multa_por_dia_de_atraso(self):
        self.assertEqual(regras.calcular_multa(date(2026, 1, 15), date(2026, 1, 16)), Decimal("0.50"))
        self.assertEqual(regras.calcular_multa(date(2026, 1, 15), date(2026, 1, 25)), Decimal("5.00"))

    def test_dias_atraso_nunca_negativo(self):
        self.assertEqual(regras.dias_atraso(date(2026, 2, 1), date(2026, 1, 1)), 0)


class FilaTests(unittest.TestCase):
    def test_sem_exemplar_disponivel_ninguem_retira(self):
        self.assertFalse(regras.pode_retirar(1, 1, 0))
        self.assertFalse(regras.pode_retirar(None, 0, 0))

    def test_sem_fila_qualquer_um_retira(self):
        self.assertTrue(regras.pode_retirar(None, 0, 1))

    def test_com_fila_so_o_primeiro_retira_quando_ha_um_exemplar(self):
        self.assertTrue(regras.pode_retirar(1, 3, 1))
        self.assertFalse(regras.pode_retirar(2, 3, 1))

    def test_quem_nao_reservou_fura_fila_nao(self):
        self.assertFalse(regras.pode_retirar(None, 1, 1))

    def test_sobra_de_exemplares_libera_quem_nao_reservou(self):
        self.assertTrue(regras.pode_retirar(None, 1, 2))
        self.assertTrue(regras.pode_retirar(2, 3, 2))


if __name__ == "__main__":
    unittest.main()
