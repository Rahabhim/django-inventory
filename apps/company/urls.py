# -*- encoding: utf-8 -*-
from models import Department, DepartmentType
from django.conf.urls.defaults import patterns, url, include
from django.views.generic import ListView
from django.utils.translation import ugettext_lazy as _
from django.views.generic.create_update import create_object, update_object
from generic_views.views import generic_delete, \
                                generic_detail, generic_list

urlpatterns = patterns('',
    url(r'^object/list/company_department$', ListView.as_view( model=Department, template_name="department_list.html" ),
            name='company_department_list'),
    url(r'^object/list/company_department_type$', generic_list, 
            dict({'queryset':DepartmentType.objects.all()}, extra_context=dict(title =_(u'department types'))),
            name='company_department_type_list'),
    # url(r'^object/list/company_locations$', ListView.as_view()),
    )

#eof