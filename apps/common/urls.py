from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template
from django.utils.translation import ugettext_lazy as _
from django.views.generic.create_update import create_object, update_object
from generic_views.views import generic_delete, \
                                generic_detail, generic_list

from models import Location, Supplier
from forms import LocationForm_view, SupplierForm

urlpatterns = patterns('common.views',
    url(r'^about/$', direct_to_template, { 'template' : 'about.html'}, 'about'),
)

urlpatterns += patterns('',
    url(r'^set_language/$', 'django.views.i18n.set_language', name='set_language'),

    url(r'^location/list/$', generic_list, dict({'queryset':Location.objects.all()}, extra_context=dict(title =_(u'locations'))), 'location_list'),
    url(r'^location/create/$', create_object, {'model':Location, 'template_name':'generic_form.html'}, 'location_create'),
    url(r'^location/(?P<object_id>\d+)/update/$', update_object, {'model':Location, 'template_name':'generic_form.html'}, 'location_update'),
    url(r'^location/(?P<object_id>\d+)/delete/$', generic_delete, dict({'model':Location}, post_delete_redirect="location_list", extra_context=dict(object_name=_(u'locations'))), 'location_delete'),
    url(r'^location/(?P<object_id>\d+)/$', generic_detail, dict(form_class=LocationForm_view, queryset=Location.objects.all()), 'location_view'),

    url(r'^supplier/(?P<object_id>\d+)/$', generic_detail, dict(form_class=SupplierForm, queryset=Supplier.objects.all()), 'supplier_view'),
    url(r'^supplier/list/$', generic_list, dict({'queryset':Supplier.objects.all()}, extra_context=dict(title=_(u'suppliers'))), 'supplier_list'),
    url(r'^supplier/create/$', create_object, {'form_class':SupplierForm, 'template_name':'generic_form.html'}, 'supplier_create'),
    url(r'^supplier/(?P<object_id>\d+)/update/$', update_object, {'form_class':SupplierForm, 'template_name':'generic_form.html'}, 'supplier_update'),
    url(r'^supplier/(?P<object_id>\d+)/delete/$', generic_delete, dict({'model':Supplier}, post_delete_redirect="supplier_list", extra_context=dict(object_name=_(u'supplier'))), 'supplier_delete'),

)
