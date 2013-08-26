# -*- encoding: utf-8 -*-
from django import forms
from generic_views.forms import DetailForm
from models import Delegate, Project, Contract
from ajax_select.fields import AutoCompleteSelectField
from django.utils.translation import ugettext_lazy as _

class DelegateForm(forms.ModelForm):
    class Meta:
        model = Delegate

class DelegateForm_view(DetailForm):
    class Meta:
        model = Delegate
        exclude = ('photos',)

class ContractForm(forms.ModelForm):
    department = AutoCompleteSelectField('department', label=_("Department"), required=False)
    class Meta:
        model = Contract

class ContractForm_view(DetailForm):
    class Meta:
        model = Contract

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project

class ProjectForm_view(DetailForm):
    class Meta:
        model = Project
#eof