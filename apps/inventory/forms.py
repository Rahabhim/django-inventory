# -*- encoding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext_lazy as _
from ajax_select.fields import AutoCompleteSelectField

from generic_views.forms import DetailForm, InlineModelForm

from models import Log, \
                   InventoryTransaction, Inventory


class LogForm(forms.ModelForm):
    class Meta:
        model = Log


class InventoryForm(forms.ModelForm):
    location = AutoCompleteSelectField('location')
    class Meta:
        model = Inventory


class InventoryForm_view(DetailForm):
    class Meta:
        model = Inventory

class InventoryTransactionForm(forms.ModelForm):
    supply = AutoCompleteSelectField('product')
    class Meta:
        model = InventoryTransaction


class InventoryTransactionForm_inline(InlineModelForm):
    supply = AutoCompleteSelectField('product')
    class Meta:
        model = InventoryTransaction
        exclude = ('notes',)


#eof
