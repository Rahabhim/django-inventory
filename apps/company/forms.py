# -*- encoding: utf-8 -*-
from django import forms
from ajax_select.fields import AutoCompleteSelectField

# from django.utils.translation import ugettext_lazy as _
from generic_views.forms import DetailForm, DetailForeignWidget
from models import Department, DepartmentType

class DepartmentForm(forms.ModelForm):
    merge = AutoCompleteSelectField('department', required=False)
    parent = AutoCompleteSelectField('department', required=False)
    serviced_by = AutoCompleteSelectField('department', required=False)
    class Meta:
        model = Department

class DepartmentForm_view(DetailForm):
    class Meta:
        model = Department
        widgets = {'merge': DetailForeignWidget(queryset=Department.objects.all()),
                    'parent': DetailForeignWidget(queryset=Department.objects.all()),
                    'serviced_by': DetailForeignWidget(queryset=Department.objects.all()),
                  }

class DepartmentTypeForm_view(DetailForm):
    class Meta:
        model = DepartmentType

#eof
