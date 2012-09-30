# -*- encoding: utf-8 -*-
from django import forms
# from django.utils.translation import ugettext_lazy as _

# from generic_views.forms import DetailForm
from models import Department, DepartmentType

class DepartmentForm_view(forms.ModelForm):
    class Meta:
        model = Department

class DepartmentTypeForm_view(forms.ModelForm):
    class Meta:
        model = DepartmentType

#eof
