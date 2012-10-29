# -*- encoding: utf-8 -*-
from models import Department, DepartmentType
from django.conf.urls.defaults import patterns, url, include
from django.views.generic import ListView
from django.utils.translation import ugettext_lazy as _
from django.views.generic.create_update import create_object, update_object
from generic_views.views import generic_delete, \
                                generic_detail, generic_list

from forms import DepartmentForm_view, DepartmentTypeForm_view
from company import department_type_filter
from lookups import _department_filter_q

dept_name_filter = {'name': 'name', 'title': _('name'), 'destination': _department_filter_q}

urlpatterns = patterns('',
    url(r'^object/list/company_department$', generic_list, dict( queryset=Department.objects.all(), \
            extra_context=dict(),
            list_filters=[dept_name_filter, department_type_filter]),
            name='company_department_list'),
    url(r'^object/list/company_department_type$', generic_list, 
            dict({'queryset':DepartmentType.objects.all()}, extra_context=dict(title =_(u'department types'))),
            name='company_department_type_list'),
    # url(r'^object/list/company_locations$', ListView.as_view()),
    
    url(r'^object/view/company_department/(?P<object_id>\d+)/$', generic_detail, dict(form_class=DepartmentForm_view, queryset=Department.objects.all()), 'company_department_view'),
    url(r'^object/view/company_department_type/(?P<object_id>\d+)/$', generic_detail, dict(form_class=DepartmentTypeForm_view, queryset=DepartmentType.objects.all()), 'company_department_type_view'),
    )

#eof