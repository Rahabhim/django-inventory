# -*- encoding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template
from django.utils.translation import ugettext_lazy as _
from generic_views.views import GenericDeleteView, GenericUpdateView, GenericCreateView, \
                                generic_detail, GenericBloatedListView

from models import Location, Supplier, LocationTemplate
from forms import LocationForm, LocationForm_view, SupplierForm, \
        LocationTemplateForm, LocationTemplateForm_view

from views import LocationListView, location_do_activate, location_do_deactivate

generic_name_filter = {'name': 'name', 'title': _('name'), 'destination':'name__icontains'}

vat_num_filter = {'name': 'vat_number', 'title': _('VAT number'), 'destination': 'vat_number'}

urlpatterns = patterns('common.views',
    url(r'^about/$', direct_to_template, { 'template' : 'about.html'}, 'about'),
)

urlpatterns += patterns('',
    url(r'^set_language/$', 'django.views.i18n.set_language', name='set_language'),

    url(r'^location/list/$', LocationListView.as_view(), name='location_list'),
    url(r'^location/create/$', GenericCreateView.as_view(model=Location, form_class=LocationForm), name='location_create'),
    url(r'^location/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(model=Location, form_class=LocationForm), name='location_update'),
    url(r'^location/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(model=Location, success_url="location_list", extra_context=dict(object_name=_(u'locations'))), name='location_delete'),
    url(r'^location/(?P<object_id>\d+)/$', generic_detail, dict(form_class=LocationForm_view, queryset=Location.objects.all()), 'location_view'),

    url(r'^location/(?P<object_id>\d+)/activate/$', location_do_activate, name='location_activate'),
    url(r'^location/(?P<object_id>\d+)/deactivate/$', location_do_deactivate, name='location_deactivate'),

    url(r'^location/template/list/$', GenericBloatedListView.as_view(queryset=LocationTemplate.objects.all(),
                extra_context=dict(title =_(u'location templates'))), name='location_template_list'),
    url(r'^location/template/(?P<object_id>\d+)/$', generic_detail, \
                dict(form_class=LocationTemplateForm_view, queryset=LocationTemplate.objects.all()),
                name='location_template_view'),
    url(r'^location/template/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(
                    model=LocationTemplate, form_class=LocationTemplateForm),
                name='location_template_update'),
    url(r'^location/template/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(
                    model=LocationTemplate, success_url="location_list",
                    extra_context=dict(object_name=_(u'location templates'))),
                name='location_template_delete'),

    url(r'^supplier/(?P<object_id>\d+)/$', generic_detail, dict(form_class=SupplierForm,
                title=_("Supplier details"), queryset=Supplier.objects.all()),
            name='supplier_view'),
    url(r'^supplier/list/$', GenericBloatedListView.as_view(queryset=Supplier.objects.by_request,
            list_filters=[generic_name_filter, vat_num_filter],
            extra_context=dict(title=_(u'Suppliers'))), name='supplier_list'),
    url(r'^supplier/create/$', GenericCreateView.as_view(form_class=SupplierForm), name='supplier_create'),
    url(r'^supplier/(?P<pk>\d+)/update/$', GenericUpdateView.as_view( form_class=SupplierForm, ), name='supplier_update'),
    url(r'^supplier/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(model=Supplier, success_url="supplier_list", extra_context=dict(object_name=_(u'supplier'))), name='supplier_delete'),

)
