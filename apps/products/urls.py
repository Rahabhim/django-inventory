# -*- encoding: utf-8 -*-
from django.conf.urls.defaults import patterns, url

from django.utils.translation import ugettext_lazy as _
from django.views.generic.create_update import create_object, update_object

from conf import settings as inventory_settings

from photos.views import generic_photos

from generic_views.views import generic_delete, \
                                generic_detail, generic_list, \
                                GenericCreateView, GenericUpdateView, \
                                GenericBloatedListView, GenericDetailView

from models import ItemTemplate, ItemCategory, Manufacturer
from forms import ItemTemplateForm, ItemTemplateForm_view, \
        ItemCategoryForm, ItemCategoryForm_view, ItemCategoryContainForm, \
        ItemCategoryContainForm_view, \
        ManufacturerForm, ManufacturerForm_view


manufacturer_filter = {'name':'manufacturer', 'title':_(u'manufacturer'), 
            'queryset':Manufacturer.objects.all(), 'destination':'manufacturer'}

category_filter = { 'name': 'category', 'title': _(u'category'),
            'queryset': ItemCategory.objects.all(), 'destination': 'category'}

product_name_filter = {'name': 'name', 'title': _('name'),
            'destination': ('description__icontains', 'model__icontains',
                            'part_number')}

generic_name_filter = {'name': 'name', 'title': _('name'), 'destination':'name__icontains'}

urlpatterns = patterns('products.views',
    url(r'^template/list/$', GenericBloatedListView.as_view(queryset=ItemTemplate.objects.all(),
            list_filters=[ manufacturer_filter, category_filter, product_name_filter],
            title=_(u'item template'),
            extra_columns=[dict(name=_(u'Manufacturer'), attribute='manufacturer'),
                            dict(name=_(u'Category'), attribute='category'),] ),
            name='template_list'),
    url(r'^template/create/$', GenericCreateView.as_view(form_class=ItemTemplateForm,
                    inline_fields=('attributes',),
                    extra_context={'object_name':_(u'item template')}),
            name='template_create'),
    url(r'^template/(?P<pk>\d+)/update/$', GenericUpdateView.as_view( \
            form_class=ItemTemplateForm, inline_fields=('attributes',),
            extra_context={'object_name':_(u'item template')}),
            name='template_update' ),
    url(r'^template/(?P<object_id>\d+)/delete/$', generic_delete,
            dict(model=ItemTemplate, post_delete_redirect="template_list",
                    extra_context=dict(object_name=_(u'item template'),
                    _message=_(u"Will be deleted from any user that may have it assigned and from any item group."))),
            'template_delete' ),
    url(r'^template/orphans/$', generic_list, dict(queryset=ItemTemplate.objects.filter(item=None),
                    extra_context=dict(title=_('orphan templates'))),
            'template_orphans_list'),
    url(r'^template/(?P<object_id>\d+)/photos/$', generic_photos, {'model':ItemTemplate, 'max_photos':inventory_settings.MAX_TEMPLATE_PHOTOS, 'extra_context':{'object_name':_(u'item template')}}, 'template_photos'),
    url(r'^template/(?P<object_id>\d+)/$', generic_detail, dict(form_class=ItemTemplateForm_view,
                    queryset=ItemTemplate.objects.all(),
                    extra_context={'object_name':_(u'item template'), \
                        'sidebar_subtemplates':['generic_photos_subtemplate.html']}),
            'template_view'),
    url(r'^template/(?P<object_id>\d+)/items/$', 'template_items', (), 'template_items_list'),
    url(r'^template/(?P<object_id>\d+)/assign/supplies$', 'template_assign_remove_supply', (), name='template_assign_supply'),
    url(r'^template/(?P<object_id>\d+)/assign/suppliers/$', 'template_assign_remove_suppliers', (), name='template_assign_suppliers'),

    url(r'^supplier/(?P<object_id>\d+)/assign/itemtemplates/$',
            'supplier_assign_remove_itemtemplates', (), 'supplier_assign_itemtemplates'),

    url(r'^categories/list/$', GenericBloatedListView.as_view(queryset=ItemCategory.objects.all(),
            list_filters=[generic_name_filter,],
            extra_columns=[{'name':_(u'Parent category'), 'attribute': 'parent'},
                        {'name':_(u'Approved'), 'attribute': 'approved'},
                        {'name':_(u'Is bundle'), 'attribute': 'is_bundle'}],
            title=_(u'list of item categories')), name='category_list'),
    url(r'^categories/create/$', create_object, {'form_class': ItemCategoryForm,
                    'template_name':'generic_form.html',
                    'extra_context':{'object_name':_(u'item category')}},
            'category_create'), # TODO: permissions?
    url(r'^categories/(?P<pk>\d+)/update/$', GenericUpdateView.as_view( \
            form_class=ItemCategoryForm, template_name= 'category_form.html',
            inline_fields={'may_contain': ItemCategoryContainForm},
            extra_context={'object_name':_(u'item category')}),
            name='category_update' ),
    url(r'^categories/(?P<object_id>\d+)/delete/$', generic_delete,
            dict(model=ItemCategory, post_delete_redirect="category_list",
                    extra_context=dict(object_name=_(u'item category'),
                    # FIXME _message=_(u"Will be deleted from any user that may have it assigned and from any item group.")
                    )),
            'category_delete' ),
    url(r'^categories/(?P<pk>\d+)/$', GenericDetailView.as_view(form_class=ItemCategoryForm_view,
                    template_name='category_form.html',
                    queryset=ItemCategory.objects.all(),
                    inline_fields={'may_contain': ItemCategoryContainForm_view},
                    extra_context={'object_name':_(u'item category'),}),
            name='category_view'),

    url(r'^manufacturers/list/$', generic_list, dict(queryset=Manufacturer.objects.all(),
            list_filters=[generic_name_filter,],
            extra_context=dict(title=_(u'manufacturer'))), 'manufacturers_list'),
    url(r'^manufacturers/create/$', create_object, {'form_class':ManufacturerForm,
                    'template_name':'generic_form.html',
                    'extra_context':{'object_name':_(u'manufacturer')}},
            'manufacturer_create'),
    url(r'^manufacturers/(?P<object_id>\d+)/update/$', update_object,
            {'form_class': ManufacturerForm, 'template_name':'generic_form.html',
                    'extra_context':{'object_name':_(u'manufacturer')}},
            'manufacturer_update' ),
    url(r'^manufacturers/(?P<object_id>\d+)/delete/$', generic_delete,
            dict(model=Manufacturer, post_delete_redirect="manufacturers_list",
                    extra_context=dict(object_name=_(u'manufacturer'),
                    # FIXME _message=_(u"Will be deleted from any user that may have it assigned and from any item group.")
                    )),
            'manufacturer_delete' ),
    url(r'^manufacturers/(?P<object_id>\d+)/$', generic_detail, dict(form_class=ManufacturerForm_view,
                    queryset=Manufacturer.objects.all(),
                    extra_context={'object_name':_(u'manufacturer'),}),
            'manufacturer_view'),

    )

#TODO: categories, attributes, manufacturers

#eof
