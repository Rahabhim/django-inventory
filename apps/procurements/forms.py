from django import forms
from generic_views.forms import DetailForm
from models import Delegate, Project, Contract


class DelegateForm(forms.ModelForm):
    class Meta:
        model = Delegate

class DelegateForm_view(DetailForm):
    class Meta:
        model = Delegate
        exclude = ('photos',)

class ContractForm(forms.ModelForm):
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