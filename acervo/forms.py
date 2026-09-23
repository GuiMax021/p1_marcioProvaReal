from django import forms

from .models import Exemplar, Livro, Membro


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
