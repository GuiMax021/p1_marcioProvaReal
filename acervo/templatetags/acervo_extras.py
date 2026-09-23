from django import template

register = template.Library()


@register.filter
def attr(obj, nome):
    """Le um atributo (ou propriedade) de um objeto pelo nome: {{ obj|attr:"titulo" }}."""
    valor = getattr(obj, nome, "")
    return valor() if callable(valor) else valor
