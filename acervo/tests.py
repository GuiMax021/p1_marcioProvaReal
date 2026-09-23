"""Testes de integracao (Django): python manage.py test"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Categoria, Emprestimo, Exemplar, Livro, Membro, Reserva
from .services import RegraDeNegocioError, cancelar_reserva, devolver, emprestar, pagar_multa, reservar


class BaseTest(TestCase):
    def setUp(self):
        cat = Categoria.objects.create(codigo="000", nome="Generalidades")
        self.livro = Livro.objects.create(titulo="Livro A", categoria=cat, ano=2020)
        self.ex = Exemplar.objects.create(livro=self.livro, codigo="001", localizacao="A1")
        self.ana = Membro.objects.create(nome="Ana", email="ana@x.com")
        self.bia = Membro.objects.create(nome="Bia", email="bia@x.com")
        self.caio = Membro.objects.create(nome="Caio", email="caio@x.com")


class EmprestimoTests(BaseTest):
    def test_emprestimo_define_prazo_de_14_dias(self):
        hoje = date(2026, 3, 1)
        emp = emprestar(self.ex, self.ana, hoje=hoje)
        self.assertEqual(emp.data_prevista, hoje + timedelta(days=14))

    def test_exemplar_emprestado_nao_pode_ser_emprestado_de_novo(self):
        emprestar(self.ex, self.ana)
        with self.assertRaises(RegraDeNegocioError):
            emprestar(self.ex, self.bia)

    def test_exemplar_digital_nao_e_emprestado(self):
        dig = Exemplar.objects.create(livro=self.livro, codigo="002", tipo="DIGITAL", localizacao="Repo")
        with self.assertRaises(RegraDeNegocioError):
            emprestar(dig, self.ana)

    def test_membro_inativo_nao_empresta(self):
        self.ana.ativo = False
        with self.assertRaises(RegraDeNegocioError):
            emprestar(self.ex, self.ana)

    def test_limite_de_3_emprestimos(self):
        cat = self.livro.categoria
        for i in range(3):
            l = Livro.objects.create(titulo=f"L{i}", categoria=cat, ano=2000)
            emprestar(Exemplar.objects.create(livro=l, codigo=f"X{i}", localizacao="Z"), self.ana)
        with self.assertRaises(RegraDeNegocioError):
            emprestar(self.ex, self.ana)

    def test_membro_com_atraso_nao_retira_outro(self):
        outro = Livro.objects.create(titulo="B", categoria=self.livro.categoria, ano=2001)
        ex2 = Exemplar.objects.create(livro=outro, codigo="002", localizacao="A2")
        emprestar(self.ex, self.ana, hoje=date.today() - timedelta(days=30))
        with self.assertRaises(RegraDeNegocioError):
            emprestar(ex2, self.ana)


class DevolucaoEMultaTests(BaseTest):
    def test_devolucao_no_prazo_sem_multa(self):
        emp = emprestar(self.ex, self.ana, hoje=date(2026, 3, 1))
        devolver(emp, hoje=date(2026, 3, 10))
        self.assertEqual(emp.multa, Decimal("0.00"))
        self.assertFalse(emp.aberto)

    def test_devolucao_atrasada_gera_multa_e_bloqueia_novo_emprestimo(self):
        emp = emprestar(self.ex, self.ana, hoje=date(2026, 3, 1))  # prevista 15/03
        devolver(emp, hoje=date(2026, 3, 25))  # 10 dias
        self.assertEqual(emp.multa, Decimal("5.00"))
        with self.assertRaises(RegraDeNegocioError):
            emprestar(self.ex, self.ana)  # multa pendente
        pagar_multa(emp)
        emprestar(self.ex, self.ana)  # liberado

    def test_devolver_duas_vezes_falha(self):
        emp = emprestar(self.ex, self.ana)
        devolver(emp)
        with self.assertRaises(RegraDeNegocioError):
            devolver(emp)


class ReservaTests(BaseTest):
    def test_pode_reservar_mesmo_com_exemplar_disponivel(self):
        # Agora é permitido fazer reserva preventiva mesmo com exemplares disponíveis
        r = reservar(self.livro, self.ana)
        self.assertEqual(r.status, Reserva.Status.ATIVA)
        self.assertEqual(r.posicao_na_fila, 1)

    def test_fila_respeita_ordem(self):
        emprestar(self.ex, self.ana)
        r1 = reservar(self.livro, self.bia)
        r2 = reservar(self.livro, self.caio)
        self.assertEqual((r1.posicao_na_fila, r2.posicao_na_fila), (1, 2))

    def test_reserva_duplicada_falha(self):
        emprestar(self.ex, self.ana)
        reservar(self.livro, self.bia)
        with self.assertRaises(RegraDeNegocioError):
            reservar(self.livro, self.bia)

    def test_so_o_primeiro_da_fila_retira_apos_devolucao(self):
        emp = emprestar(self.ex, self.ana)
        reservar(self.livro, self.bia)
        reservar(self.livro, self.caio)
        devolver(emp)
        with self.assertRaises(RegraDeNegocioError):
            emprestar(self.ex, self.caio)  # 2º da fila
        with self.assertRaises(RegraDeNegocioError):
            emprestar(self.ex, self.ana)  # nao reservou
        emprestar(self.ex, self.bia)  # 1º da fila
        self.assertEqual(Reserva.objects.get(membro=self.bia).status, Reserva.Status.ATENDIDA)
        self.assertEqual(Reserva.objects.get(membro=self.caio).posicao_na_fila, 1)

    def test_cancelar_reserva_libera_posicao(self):
        emprestar(self.ex, self.ana)
        r1 = reservar(self.livro, self.bia)
        r2 = reservar(self.livro, self.caio)
        cancelar_reserva(r1)
        self.assertEqual(r2.posicao_na_fila, 1)


class ViewsTests(BaseTest):
    def setUp(self):
        super().setUp()
        get_user_model().objects.create_user("admin", password="x12345678")

    def test_exige_login(self):
        self.assertEqual(self.client.get(reverse("livro_lista")).status_code, 302)

    def test_paginas_principais(self):
        self.client.login(username="admin", password="x12345678")
        for nome in ["home", "livro_lista", "exemplar_lista", "autor_lista", "categoria_lista",
                     "membro_lista", "emprestimo_lista", "reserva_lista", "emprestimo_criar", "reserva_criar"]:
            self.assertEqual(self.client.get(reverse(nome)).status_code, 200, nome)
        self.assertEqual(self.client.get(reverse("livro_detalhe", args=[self.livro.pk])).status_code, 200)

    def test_fluxo_emprestar_e_devolver_pela_view(self):
        self.client.login(username="admin", password="x12345678")
        self.client.post(reverse("emprestimo_criar"), {"membro": self.ana.pk, "exemplar": self.ex.pk})
        emp = Emprestimo.objects.get()
        self.assertTrue(emp.aberto)
        self.client.post(reverse("emprestimo_devolver", args=[emp.pk]))
        emp.refresh_from_db()
        self.assertFalse(emp.aberto)

    def test_excluir_livro_com_emprestimo_e_protegido(self):
        self.client.login(username="admin", password="x12345678")
        emprestar(self.ex, self.ana)
        self.client.post(reverse("exemplar_excluir", args=[self.ex.pk]))
        self.assertTrue(Exemplar.objects.filter(pk=self.ex.pk).exists())


class BuscaEFiltroLivrosTests(BaseTest):
    """Feature 1: busca por texto + filtros na listagem de livros."""

    def setUp(self):
        super().setUp()
        from .models import Autor
        self.client.force_login(get_user_model().objects.create_user("u", password="x12345678"))
        cat2 = Categoria.objects.create(codigo="800", nome="Literatura")
        self.autor = Autor.objects.create(nome="Machado de Assis")
        self.livro.autores.add(Autor.objects.create(nome="Maria Fernandes"))
        self.livro2 = Livro.objects.create(titulo="Contos Completos", categoria=cat2, ano=1899)
        self.livro2.autores.add(self.autor)
        self.ex2 = Exemplar.objects.create(livro=self.livro2, codigo="002", localizacao="I1")

    def titulos(self, **params):
        resp = self.client.get(reverse("livro_lista"), params)
        self.assertEqual(resp.status_code, 200)
        return {l.titulo for l in resp.context["object_list"]}

    def test_sem_filtros_lista_tudo(self):
        self.assertEqual(self.titulos(), {"Livro A", "Contos Completos"})

    def test_busca_por_titulo_sem_diferenciar_maiusculas(self):
        self.assertEqual(self.titulos(q="contos"), {"Contos Completos"})

    def test_busca_por_autor(self):
        self.assertEqual(self.titulos(q="machado"), {"Contos Completos"})

    def test_filtro_por_categoria(self):
        self.assertEqual(self.titulos(categoria=self.livro.categoria.pk), {"Livro A"})

    def test_filtro_disponivel_e_emprestado(self):
        emprestar(self.ex, self.ana)
        self.assertEqual(self.titulos(status="disponivel"), {"Contos Completos"})
        self.assertEqual(self.titulos(status="emprestado"), {"Livro A"})

    def test_filtros_combinados(self):
        self.assertEqual(self.titulos(q="livro", categoria=self.livro.categoria.pk, status="disponivel"), {"Livro A"})
        self.assertEqual(self.titulos(q="livro", categoria=self.livro2.categoria.pk), set())

    def test_sem_resultado_mostra_mensagem_e_mantem_termo(self):
        resp = self.client.get(reverse("livro_lista"), {"q": "inexistente"})
        self.assertContains(resp, "Nenhum livro encontrado")
        self.assertContains(resp, 'value="inexistente"')

    def test_categoria_invalida_e_ignorada(self):
        self.assertEqual(self.titulos(categoria="abc"), {"Livro A", "Contos Completos"})


class ValidacaoAnoLivroTests(BaseTest):
    """Feature 2: ano de publicacao nao pode ser futuro."""

    def dados(self, ano):
        from .models import Autor
        autor = Autor.objects.create(nome=f"Autor {ano}")
        return {"titulo": "Novo", "autores": [autor.pk], "categoria": self.livro.categoria.pk, "ano": ano, "editora": "X"}

    def test_ano_futuro_e_rejeitado(self):
        from django.utils import timezone
        from .forms import LivroForm
        form = LivroForm(self.dados(timezone.localdate().year + 1))
        self.assertFalse(form.is_valid())
        self.assertIn("ano", form.errors)
        self.assertIn("não pode ser futuro", form.errors["ano"][0])

    def test_ano_atual_e_passado_sao_aceitos(self):
        from django.utils import timezone
        from .forms import LivroForm
        self.assertTrue(LivroForm(self.dados(timezone.localdate().year)).is_valid())
        self.assertTrue(LivroForm(self.dados(1899)).is_valid())

    def test_erro_aparece_na_tela_e_nao_grava(self):
        from django.utils import timezone
        self.client.force_login(get_user_model().objects.create_user("u", password="x12345678"))
        resp = self.client.post(reverse("livro_criar"), self.dados(timezone.localdate().year + 5))
        self.assertContains(resp, "não pode ser futuro")
        self.assertFalse(Livro.objects.filter(titulo="Novo").exists())
