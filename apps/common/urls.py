from django.db.models import Q
from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template
from django.utils.translation import ugettext_lazy as _
from generic_views.views import GenericDeleteView, GenericUpdateView, GenericCreateView, \
                                generic_detail, generic_list, GenericBloatedListView

from models import Location, Supplier, LocationTemplate
from forms import LocationForm, LocationForm_view, SupplierForm, LocationTemplateForm_view

from company.models import Department
from company.lookups import _department_filter_q

location_dept_filter = {'name': 'dept', 'title': _('department'), 
            'destination': lambda q: Q(department__in=Department.objects.filter(_department_filter_q(q)))}

urlpatterns = patterns('common.views',
    url(r'^about/$', direct_to_template, { 'template' : 'about.html'}, 'about'),
)

urlpatterns += patterns('',
    url(r'^set_language/$', 'django.views.i18n.set_language', name='set_language'),

    url(r'^location/list/$', GenericBloatedListView.as_view(queryset=Location.objects.all(), 
                list_filters=[location_dept_filter],
                prefetch_fields=('department',),
                extra_context=dict(title =_(u'locations'))), name='location_list'),
    url(r'^location/create/$', GenericCreateView.as_view(model=Location, form_class= LocationForm), name='location_create'),
    url(r'^location/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(model=Location), name='location_update'),
    url(r'^location/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(model=Location, success_url="location_list", extra_context=dict(object_name=_(u'locations'))), name='location_delete'),
    url(r'^location/(?P<object_id>\d+)/$', generic_detail, dict(form_class=LocationForm_view, queryset=Location.objects.all()), 'location_view'),

    url(r'^location/template/list/$', GenericBloatedListView.as_view(queryset=LocationTemplate.objects.all(),
                extra_context=dict(title =_(u'location templates'))), name='location_template_list'),
    url(r'^location/template/(?P<object_id>\d+)/$', generic_detail, \
                dict(form_class=LocationTemplateForm_view, queryset=LocationTemplate.objects.all()),
                name='location_template_view'),
    
    url(r'^supplier/(?P<object_id>\d+)/$', generic_detail, dict(form_class=SupplierForm,
                title=_("Supplier details"), queryset=Supplier.objects.all()),
            name='supplier_view'),
    url(r'^supplier/list/$', generic_list, dict({'queryset':Supplier.objects.all()}, 
            extra_context=dict(title=_(u'Suppliers'))), 'supplier_list'),
    url(r'^supplier/create/$', GenericCreateView.as_view(form_class=SupplierForm), name='supplier_create'),
    url(r'^supplier/(?P<pk>\d+)/update/$', GenericUpdateView.as_view( form_class=SupplierForm, ), name='supplier_update'),
    url(r'^supplier/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(model=Supplier, success_url="supplier_list", extra_context=dict(object_name=_(u'supplier'))), name='supplier_delete'),

)
