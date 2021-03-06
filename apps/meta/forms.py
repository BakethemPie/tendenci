from django import forms
from meta.models import Meta as MetaTag

class MetaForm(forms.ModelForm):
    class Meta:
        model = MetaTag
        fields = (
            'title',
            'keywords',
            'description',
            'canonical_url',
        )