from django import forms
from generic_views.forms import DetailForm
from models import ItemTemplate


class ItemTemplateForm(forms.ModelForm):
    class Meta:
        model = ItemTemplate
        exclude = ('photos', 'supplies', 'suppliers')


class ItemTemplateForm_view(DetailForm):
    class Meta:
        model = ItemTemplate
        exclude = ('photos',)

#eof