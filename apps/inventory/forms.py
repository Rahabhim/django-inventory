from django import forms
from django.utils.translation import ugettext_lazy as _


from generic_views.forms import DetailForm

from models import Log, \
                   InventoryTransaction, Inventory


class LogForm(forms.ModelForm):
    class Meta:
        model = Log


class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory


class InventoryForm_view(DetailForm):
    class Meta:
        model = Inventory

class InventoryTransactionForm(forms.ModelForm):
    class Meta:
        model = InventoryTransaction



#eof
