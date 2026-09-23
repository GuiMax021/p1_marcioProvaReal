from django import forms
from django.utils import timezone

from .models import Exemplar, Livro, Membro


class LivroForm(forms.ModelForm):
    """Cadastro/edicao de livro, com validacao propria do dominio (Feature 2)."""

    class Meta:
        model = Livro
        fields = ["titulo", "autores", "categoria", "ano", "editora"]

    def clean_ano(self):
        ano = self.cleaned_data.get("ano")
        ano_atual = timezone.localdate().year
        if ano is not None and ano > ano_atual:
            raise forms.ValidationError(
                f"O ano de publicação não pode ser futuro (máximo permitido: {ano_atual})."
            )
        return ano


class EmprestimoForm(forms.Form):
    membro = forms.ModelChoiceField(queryset=Membro.objects.none())
    exemplar = forms.ModelChoiceField(
        queryset=Exemplar.objects.none(), help_text="Somente exemplares físicos disponíveis."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["membro"].queryset = Membro.objects.filter(ativo=True)
        self.fields["exemplar"].queryset = Exemplar.objects.disponiveis().select_related("livro")


class ReservaForm(forms.Form):
    livro = forms.ModelChoiceField(queryset=Livro.objects.none())
    membro = forms.ModelChoiceField(queryset=Membro.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["livro"].queryset = Livro.objects.all()
        self.fields["membro"].queryset = Membro.objects.filter(ativo=True)
