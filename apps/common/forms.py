# -*- encoding: utf-8 -*-
from django import forms
# from django.utils.translation import ugettext_lazy as _

from generic_views.forms import DetailForm
from models import Location, Supplier

class LocationForm_view(DetailForm):
    class Meta:
        model = Location

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier

#eof
