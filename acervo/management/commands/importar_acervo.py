"""
Importa data/acervo.csv (Aulas 04 e 05) para o banco.

Uso:  python manage.py importar_acervo [--demo]
E idempotente: itens cujo codigo/tombo ja existe sao ignorados.
"""
import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from acervo.models import Autor, Categoria, Exemplar, Livro, Membro

CATEGORIAS = {
    "000": "Generalidades e Informação",
    "100": "Filosofia e Psicologia",
    "200": "Religião e Teologia",
    "300": "Ciências Sociais e Direito",
    "400": "Linguística e Idiomas",
    "500": "Ciências Puras (Exatas e Naturais)",
    "600": "Ciências Aplicadas (Tecnologia)",
    "700": "Artes e Recreação",
    "800": "Literatura",
    "900": "História e Geografia",
}
TIPOS = {"Fisico": Exemplar.Tipo.FISICO, "Digital": Exemplar.Tipo.DIGITAL}
MEMBROS_DEMO = [
    ("Ana Souza", "ana@exemplo.com"),
    ("Bruno Lima", "bruno@exemplo.com"),
    ("Carla Dias", "carla@exemplo.com"),
]


class Command(BaseCommand):
    help = "Importa o acervo de data/acervo.csv"

    def add_arguments(self, parser):
        parser.add_argument("--csv", default=str(Path(settings.BASE_DIR) / "data" / "acervo.csv"))
        parser.add_argument("--demo", action="store_true", help="Cria também 3 membros de exemplo")

    @transaction.atomic
    def handle(self, *args, **opts):
        for codigo, nome in CATEGORIAS.items():
            Categoria.objects.update_or_create(codigo=codigo, defaults={"nome": nome})

        criados = ignorados = 0
        with open(opts["csv"], newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if Exemplar.objects.filter(codigo=row["Codigo"]).exists():
                    ignorados += 1
                    continue
                livro, _ = Livro.objects.get_or_create(
                    titulo=row["Titulo"], ano=int(row["Ano"]),
                    defaults={
                        "categoria": Categoria.objects.get(codigo=row["Categoria_Codigo"]),
                        "editora": row["Editora"],
                    },
                )
                autor, _ = Autor.objects.get_or_create(nome=row["Autor"])
                livro.autores.add(autor)
                Exemplar.objects.create(
                    livro=livro, codigo=row["Codigo"],
                    tipo=TIPOS[row["Tipo_Acervo"]], localizacao=row["Localizacao"],
                )
                criados += 1

        if opts["demo"]:
            for nome, email in MEMBROS_DEMO:
                Membro.objects.get_or_create(email=email, defaults={"nome": nome})

        self.stdout.write(self.style.SUCCESS(f"{criados} exemplares importados, {ignorados} já existiam."))
