Relatorio

O projeto é um sistema Django para uma biblioteca. Ele empresta livros, controla uma fila de reserva e calcula multa por atraso.

Onde fica cada coisa
models.py define as tabelas: Categoria, Autor, Livro, Exemplar, Membro, Empréstimo e Reserva. O Livro é a obra e o Exemplar é a cópia física ou digital. O empréstimo é feito sobre o exemplar, e a reserva é feita sobre o livro.
regras.py guarda as contas puras, sem banco de dados. Ela calcula o prazo (14 dias), a multa (R$ 0,50 por dia de atraso) e decide quem pode retirar um livro quando há fila.
services.py faz as operações de verdade: emprestar, devolver, reservar, cancelar reserva e quitar multa. Cada uma confere as regras antes de gravar e, se alguma for violada, avisa o usuário com uma mensagem clara.
views.py liga as telas aos serviços. Tem o CRUD de cada cadastro (livros, autores, categorias, exemplares e membros), a tela de empréstimos e a de reservas.
forms.py tem o LivroForm (com a validação do ano) e os formulários de empréstimo e reserva.
templates/ são as páginas HTML.
tests.py e tests_regras.py são os testes automatizados.
importar_acervo.py é o comando que carrega o acervo.csv das Aulas 04 e 05 no banco.
Como funciona o fluxo principal
Ao emprestar, o sistema confere se o membro está ativo, se o exemplar é físico e está livre, se o membro não passou de 3 empréstimos e se não tem atraso ou multa pendente. Também confere a fila de reserva. Se tudo estiver certo, cria o empréstimo com devolução prevista em 14 dias.
Ao devolver, ele registra a data e calcula a multa se houve atraso.
Se não há exemplar livre, o membro reserva e entra na fila. Quando um exemplar volta, só o primeiro da fila consegue retirá-lo.
As duas features do professor
Busca e filtro (LivroLista em views.py): a view lê request.GET.get e filtra os livros por título ou autor com icontains e Q(). Também filtra por categoria e por disponibilidade, e os filtros funcionam juntos ou separados.
Validação (clean_ano em forms.py): se o ano de publicação for maior que o ano atual, levanta ValidationError e o livro não é salvo.