from models import Department, DepartmentType
from django.conf.urls.defaults import patterns, url, include
from django.views.generic import ListView

urlpatterns = patterns('',
    url(r'^object/list/company_department$', ListView.as_view( model=Department, ),
            name='company_department_list'),
    url(r'^object/list/company_department_type$', ListView.as_view( model=DepartmentType,),
            name='company_department_type_list'),
    # url(r'^object/list/company_locations$', ListView.as_view()),
    )

#eof