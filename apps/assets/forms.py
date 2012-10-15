# -*- encoding: utf-8 -*-
from django import forms
# from django.utils.translation import ugettext_lazy as _

from generic_views.forms import DetailForm

from models import Item, ItemGroup
from ajax_select.fields import AutoCompleteSelectField

class ItemForm(forms.ModelForm):
    item_template = AutoCompleteSelectField('product')
    location = AutoCompleteSelectField('location', required=False)
    class Meta:
        model = Item
        exclude = ('photos', 'active')


class ItemForm_view(DetailForm):
    class Meta:
        model = Item
        exclude = ('photos', 'active')

class ItemGroupForm(ItemForm):
    class Meta:
        model = ItemGroup
        exclude = ('items',)

class ItemGroupForm_view(DetailForm):
    class Meta:
        model = ItemGroup
