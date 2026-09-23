from django.urls import path

from . import views as v

urlpatterns = [
    path("", v.HomeView.as_view(), name="home"),
    path("livros/<int:pk>/", v.LivroDetalhe.as_view(), name="livro_detalhe"),
    path("emprestimos/", v.EmprestimoLista.as_view(), name="emprestimo_lista"),
    path("emprestimos/novo/", v.EmprestimoCriar.as_view(), name="emprestimo_criar"),
    path("emprestimos/<int:pk>/devolver/", v.EmprestimoDevolver.as_view(), name="emprestimo_devolver"),
    path("emprestimos/<int:pk>/pagar-multa/", v.EmprestimoPagarMulta.as_view(), name="emprestimo_pagar"),
    path("reservas/", v.ReservaLista.as_view(), name="reserva_lista"),
    path("reservas/nova/", v.ReservaCriar.as_view(), name="reserva_criar"),
    path("reservas/<int:pk>/cancelar/", v.ReservaCancelar.as_view(), name="reserva_cancelar"),
]

# CRUDs padrao: /<prefixo>s/, /<prefixo>s/novo/, /<prefixo>s/<pk>/editar/, /<prefixo>s/<pk>/excluir/
_cruds = {
    "categoria": "Categoria", "autor": "Autor", "livro": "Livro",
    "exemplar": "Exemplar", "membro": "Membro",
}
_plural = {"categoria": "categorias", "autor": "autores", "livro": "livros",
           "exemplar": "exemplares", "membro": "membros"}
for _p, _n in _cruds.items():
    _base = _plural[_p]
    urlpatterns += [
        path(f"{_base}/", getattr(v, f"{_n}Lista").as_view(), name=f"{_p}_lista"),
        path(f"{_base}/novo/", getattr(v, f"{_n}Criar").as_view(), name=f"{_p}_criar"),
        path(f"{_base}/<int:pk>/editar/", getattr(v, f"{_n}Editar").as_view(), name=f"{_p}_editar"),
        path(f"{_base}/<int:pk>/excluir/", getattr(v, f"{_n}Excluir").as_view(), name=f"{_p}_excluir"),
    ]
