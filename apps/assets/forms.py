from django import forms
# from django.utils.translation import ugettext_lazy as _

from generic_views.forms import DetailForm

from models import Item, ItemGroup



class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        exclude = ('photos', 'active')


class ItemForm_view(DetailForm):
    class Meta:
        model = Item
        exclude = ('photos', 'active')

class ItemGroupForm(forms.ModelForm):
    class Meta:
        model = ItemGroup
        exclude = ('items',)

class ItemGroupForm_view(DetailForm):
    class Meta:
        model = ItemGroup
