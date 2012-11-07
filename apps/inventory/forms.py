# -*- encoding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext_lazy as _
from ajax_select.fields import AutoCompleteSelectField

from generic_views.forms import DetailForm, InlineModelForm, ReadOnlyInput

from models import Log, Inventory, InventoryItem


class LogForm(forms.ModelForm):
    class Meta:
        model = Log


class InventoryForm(forms.ModelForm):
    location = AutoCompleteSelectField('location', show_help_text=False)

    class Meta:
        model = Inventory
        exclude = ('create_user', 'validate_user', 'date_val')

    def _pre_save_by_user(self, user):
        if not self.instance.create_user_id:
            self.instance.create_user = user


class InventoryForm_view(DetailForm):
    class Meta:
        model = Inventory

class InventoryItemForm(forms.ModelForm):
    asset = AutoCompleteSelectField('item', show_help_text=False)
    class Meta:
        model = InventoryItem


class InventoryItemForm_inline(InlineModelForm):
    asset = AutoCompleteSelectField('item', show_help_text=False)
    quantity = forms.fields.IntegerField(required=False, widget=ReadOnlyInput)
    class Meta:
        model = InventoryItem
        exclude = ('notes',)

#eof
