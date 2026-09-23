# Relatório P1 — Features obrigatórias (Biblioteca / Acervo)

> Rascunho: leia, entenda e reescreva com suas palavras antes de entregar.

**Feature 1 — Busca e filtro na listagem de livros.** Escolhi buscar por **título ou autor** e filtrar por
**disponibilidade (disponível/emprestado)** e por **categoria CDD**, porque são as três perguntas que quem
usa uma biblioteca faz na prática: "que livro é esse?", "de quem?" e "posso levar hoje?". Os filtros funcionam
juntos ou separados (`request.GET.get`, `icontains`, e `Q()` para buscar título OU autor na mesma consulta —
o desafio extra) e o termo digitado continua no campo após a pesquisa. O filtro de disponibilidade usa o
mesmo critério das regras de empréstimo (exemplar físico sem empréstimo aberto), então a tela nunca mostra como
"disponível" um livro que o sistema recusaria emprestar. Sem essa feature, com 30 itens (e mais no futuro) o
atendente teria de percorrer a lista inteira para achar uma obra ou saber se há exemplar livre.

**Feature 2 — Validação `clean_ano` no formulário de livro.** Escolhi a regra "o ano de publicação não pode ser
futuro" (`LivroForm.clean_ano`, que levanta `forms.ValidationError`). O Django só garante que `ano` seja um número
positivo; nada impede digitar 2099 por engano (ex.: 2029 em vez de 2019). Sem a regra, o acervo passaria a ter
dados impossíveis, que distorcem relatórios e ordenações por ano — e, num acervo de biblioteca, um livro ainda
não publicado não pode existir como item catalogado. A mensagem aparece no próprio formulário de cadastro/edição
(`{{ form.as_p }}`) e o livro não é gravado.

**Commits:** um por feature (`Feature 1: ...` e `Feature 2: ...`) — veja `git log --oneline`.
