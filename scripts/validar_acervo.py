"""
Aula 05 - Validacao e resumo do acervo.

Le data/acervo.csv, confere se todo item possui Tipo_Acervo (Digital/Fisico)
e Categoria_Codigo validos (000 a 900), e imprime um resumo quantitativo.
"""
import csv
from collections import Counter
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "acervo.csv"
CATEGORIAS_VALIDAS = {"000", "100", "200", "300", "400", "500", "600", "700", "800", "900"}
TIPOS_VALIDOS = {"Digital", "Fisico"}


def carregar_acervo():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validar(registros):
    erros = []
    for r in registros:
        if r["Categoria_Codigo"] not in CATEGORIAS_VALIDAS:
            erros.append(f'Codigo {r["Codigo"]}: categoria invalida "{r["Categoria_Codigo"]}"')
        if r["Tipo_Acervo"] not in TIPOS_VALIDOS:
            erros.append(f'Codigo {r["Codigo"]}: tipo de acervo invalido "{r["Tipo_Acervo"]}"')
    return erros


def resumir(registros):
    por_categoria = Counter(f'{r["Categoria_Codigo"]} - {r["Categoria_Nome"]}' for r in registros)
    por_tipo = Counter(r["Tipo_Acervo"] for r in registros)
    return por_categoria, por_tipo


if __name__ == "__main__":
    registros = carregar_acervo()
    erros = validar(registros)

    print(f"Total de itens no acervo: {len(registros)}\n")

    if erros:
        print("Inconsistencias encontradas:")
        for e in erros:
            print(f"  - {e}")
    else:
        print("Nenhuma inconsistencia encontrada.\n")

    por_categoria, por_tipo = resumir(registros)

    print("Itens por Tipo de Acervo:")
    for tipo, qtd in por_tipo.items():
        print(f"  {tipo}: {qtd}")

    print("\nItens por Categoria:")
    for cat, qtd in sorted(por_categoria.items()):
        print(f"  {cat}: {qtd}")
