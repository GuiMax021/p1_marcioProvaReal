from django.contrib import admin

from .models import Autor, Categoria, Emprestimo, Exemplar, Livro, Membro, Reserva


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome")


@admin.register(Autor)
class AutorAdmin(admin.ModelAdmin):
    search_fields = ("nome",)


class ExemplarInline(admin.TabularInline):
    model = Exemplar
    extra = 0


@admin.register(Livro)
class LivroAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "ano", "editora")
    list_filter = ("categoria",)
    search_fields = ("titulo", "autores__nome")
    inlines = [ExemplarInline]


@admin.register(Exemplar)
class ExemplarAdmin(admin.ModelAdmin):
    list_display = ("codigo", "livro", "tipo", "localizacao")
    list_filter = ("tipo",)


@admin.register(Membro)
class MembroAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome", "email")


@admin.register(Emprestimo)
class EmprestimoAdmin(admin.ModelAdmin):
    list_display = ("exemplar", "membro", "data_emprestimo", "data_prevista", "data_devolucao", "multa", "multa_paga")
    list_filter = ("multa_paga",)


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("livro", "membro", "criada_em", "status")
    list_filter = ("status",)
