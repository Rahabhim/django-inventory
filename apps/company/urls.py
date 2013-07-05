# -*- encoding: utf-8 -*-
from models import Department, DepartmentType
from django.conf.urls.defaults import patterns, url
from django.views.generic import ListView
from django.utils.translation import ugettext_lazy as _
# from django.views.generic.create_update import create_object, update_object
from generic_views.views import GenericDeleteView, \
                                generic_list, \
                                GenericBloatedListView, GenericDetailView, \
                                GenericUpdateView

from forms import DepartmentForm, DepartmentForm_view, DepartmentTypeForm_view
from company import department_type_filter
from lookups import _department_filter_q

dept_name_filter = {'name': 'name', 'title': _('name'), 'destination': _department_filter_q}
dept_code_filter = {'name': 'code', 'title': _('code'), 'destination': ('code', 'code2')}
generic_name_filter = {'name': 'name', 'title': _('name'), 'destination':'name__icontains'}

urlpatterns = patterns('',
    url(r'^object/list/company_department$', GenericBloatedListView.as_view( \
            queryset=Department.objects.all(),
            extra_context=dict(),
            list_filters=[dept_name_filter, dept_code_filter, department_type_filter],
            extra_columns=[{'name': _('code'), 'attribute': 'code'},
                    {'name': _('code 2'), 'attribute': 'code2'},
                    {'name': _("Parent dept."), 'attribute': 'parent'}],
            ),
        name='company_department_list'),
    url(r'^object/list/company_department_type$', GenericBloatedListView.as_view( \
            queryset=DepartmentType.objects.all(),
            list_filters=[generic_name_filter,],
            title =_(u'department types')),
            name='company_department_type_list'),
    # url(r'^object/list/company_locations$', ListView.as_view()),
    
    url(r'^object/view/company_department/(?P<pk>\d+)/$', GenericDetailView.as_view( \
                form_class=DepartmentForm_view,
                template_name="department_form.html",
                queryset=Department.objects.all()),
            name='company_department_view'),
    url(r'^object/view/company_department_type/(?P<pk>\d+)/$', GenericDetailView.as_view( \
                form_class=DepartmentTypeForm_view, queryset=DepartmentType.objects.all()),
            name='company_department_type_view'),
    url(r'^object/update/company_department/(?P<pk>\d+)/$', GenericUpdateView\
                .as_view(model=Department, form_class=DepartmentForm), name='department_update'),

    )

#eof