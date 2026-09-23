# p1-marcio — Biblioteca / Acervo (MVP)

Projeto da disciplina (**Opção 1 – Biblioteca / Acervo**): empréstimos com **fila de reserva** e **cálculo de multa**.
Evolui o levantamento de acervo das **Aulas 04 e 05** (CDD, tipo Físico/Digital) para uma aplicação Django.

## Entidades

| Entidade | Papel |
|---|---|
| `Categoria` | Classe CDD (000–900), vinda de `docs/categorias_cdd.md` |
| `Autor` / `Livro` | Obra (N autores por livro, 1 categoria) |
| `Exemplar` | Item do acervo: `tipo` Físico/Digital, código/tombo, localização |
| `Membro` | Usuário da biblioteca (pode estar inativo) |
| `Emprestimo` | Exemplar + membro, prazo, devolução e multa |
| `Reserva` | Fila de espera por livro (ATIVA / ATENDIDA / CANCELADA) |

## Regras de negócio (`acervo/regras.py` e `acervo/services.py`)

- Prazo de **14 dias**; multa de **R$ 0,50 por dia** de atraso (o dia limite não gera multa).
- Só exemplares **físicos** são emprestados; digitais são de acesso pelo repositório.
- Um exemplar não pode ter dois empréstimos abertos (validado no serviço **e** por constraint no banco).
- Máximo de **3 empréstimos simultâneos**; sem atraso nem multa pendente para retirar outro; não pode pegar 2 cópias do mesmo livro.
- **Reserva** só quando não há exemplar livre; uma reserva ativa por membro/livro.
- **Fila**: exemplares livres são guardados para os primeiros da fila (por ordem de reserva); ao retirar, a reserva vira ATENDIDA e a fila anda.
- Multa é gravada na devolução e precisa ser quitada para novos empréstimos.

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py makemigrations acervo
python manage.py migrate
python manage.py createsuperuser
python manage.py importar_acervo --demo     # carrega data/acervo.csv (+ 3 membros de exemplo)
python manage.py runserver                  # http://127.0.0.1:8000  (admin em /admin/)
```

## Testes

```bash
python -m unittest acervo.tests_regras   # regras puras, sem banco
python manage.py test                    # integração: serviços, fila, multa e views
```

## Estrutura

```
├── manage.py / requirements.txt
├── config/            # settings, urls, wsgi
├── acervo/            # app Django
│   ├── models.py  regras.py  services.py  forms.py  views.py  urls.py  admin.py
│   ├── management/commands/importar_acervo.py
│   ├── templates/  templatetags/
│   └── tests.py  tests_regras.py
├── data/              # acervo.csv (fonte) e acervo_consolidado.xlsx (Aulas 04/05)
├── docs/categorias_cdd.md
└── scripts/           # validar_acervo.py, gerar_planilha.py (Aulas 04/05)
```

## Roteiro para o P2

Multi-organização (rede de unidades: `Unidade` FK em Exemplar/Membro/Empréstimo), papéis
(bibliotecário × leitor), dashboard e API REST com DRF reutilizando `services.py`.
