# -*- encoding: utf-8 -*-
from django.conf.urls.defaults import patterns, url

from django.utils.translation import ugettext_lazy as _
from django.views.generic.create_update import create_object, update_object

from conf import settings as inventory_settings

from photos.views import generic_photos

from generic_views.views import generic_detail, generic_list, \
                                GenericCreateView, GenericUpdateView, \
                                GenericBloatedListView, GenericDetailView, \
                                GenericDeleteView

from models import ItemTemplate, ItemCategory, Manufacturer, \
        ProductAttribute #, ProductAttributeValue
from forms import ItemTemplateForm, ItemTemplateForm_view, \
        ItemCategoryForm, ItemCategoryForm_view, ItemCategoryContainForm, \
        ItemCategoryContainForm_view, \
        ManufacturerForm, ManufacturerForm_view, \
        ProductAttributeForm, ProductAttributeForm_view, \
        ProductAttributeValueForm, ProductAttributeValueForm_view

from assets.views import TemplateAssetsView

manufacturer_filter = {'name':'manufacturer', 'title': _(u'manufacturer'),
            'queryset':Manufacturer.objects.all(), 'destination':'manufacturer'}

category_filter = { 'name': 'category', 'title': _(u'category'),
            'queryset': ItemCategory.objects.all(), 'destination': 'category'}

attrib_cat_filter = { 'name': 'category', 'title': _(u'category'),
            'queryset': ItemCategory.objects.all(), 'destination': 'applies_category'}

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
    url(r'^template/(?P<pk>\d+)/delete/$', GenericDeleteView.\
                as_view(model=ItemTemplate, success_url="template_list",
                    extra_context=dict(object_name=_(u'item template'),
                    _message=_(u"Will be deleted from any user that may have it assigned and from any item group."))),
            name='template_delete' ),
    url(r'^template/orphans/$', generic_list, dict(queryset=ItemTemplate.objects.filter(item=None),
                    extra_context=dict(title=_('orphan templates'))),
            'template_orphans_list'),
    url(r'^template/(?P<object_id>\d+)/photos/$', generic_photos, {'model':ItemTemplate, 'max_photos':inventory_settings.MAX_TEMPLATE_PHOTOS, 'extra_context':{'object_name':_(u'item template')}}, 'template_photos'),
    url(r'^template/(?P<object_id>\d+)/$', generic_detail, dict(form_class=ItemTemplateForm_view,
                    queryset=ItemTemplate.objects.all(),
                    extra_context={'object_name':_(u'item template'), \
                        'sidebar_subtemplates':['generic_photos_subtemplate.html']}),
            'template_view'),
    url(r'^template/(?P<product_id>\d+)/items/$', TemplateAssetsView.as_view(), name='template_items_list'),
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
            inline_fields={'may_contain': ItemCategoryContainForm,
                        'attributes': ProductAttributeForm},
            extra_context={'object_name':_(u'item category')}),
            name='category_update' ),
    url(r'^categories/(?P<pk>\d+)/delete/$', GenericDeleteView.\
            as_view(model=ItemCategory, success_url="category_list",
                    extra_context=dict(object_name=_(u'item category'),
                    # FIXME _message=_(u"Will be deleted from any user that may have it assigned and from any item group.")
                    )),
            name='category_delete' ),
    url(r'^categories/(?P<pk>\d+)/$', GenericDetailView.as_view(form_class=ItemCategoryForm_view,
                    template_name='category_form.html',
                    queryset=ItemCategory.objects.all(),
                    inline_fields={'may_contain': ItemCategoryContainForm_view,
                            'attributes': ProductAttributeForm_view },
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
    url(r'^manufacturers/(?P<pk>\d+)/delete/$', GenericDeleteView.\
            as_view(model=Manufacturer, success_url="manufacturers_list",
                    extra_context=dict(object_name=_(u'manufacturer'))),
            name='manufacturer_delete' ),
    url(r'^manufacturers/(?P<object_id>\d+)/$', generic_detail, dict(form_class=ManufacturerForm_view,
                    queryset=Manufacturer.objects.all(),
                    extra_context={'object_name':_(u'manufacturer'),}),
            'manufacturer_view'),

    url(r'^attributes/list/$', GenericBloatedListView.as_view(queryset=ProductAttribute.objects.all(),
            list_filters=[attrib_cat_filter, generic_name_filter,],
            extra_columns=[ {'name': _("Sequence"), 'attribute': 'sequence'},
                        {'name':_(u'short name'), 'attribute': 'short_name'},
                        {'name':_(u'Required'), 'attribute': 'required'}],
            title=_(u'list of attributes')), name='attributes_list'),
    url(r'^attributes/create/$', GenericCreateView.as_view(form_class=ProductAttributeForm,
                    extra_context={'title': _("Create attribute")}),
            name='attributes_create'),
    url(r'^attributes/(?P<pk>\d+)/update/$', GenericUpdateView.as_view( \
            form_class=ProductAttributeForm, template_name= 'attribute_form.html',
            inline_fields={'values': ProductAttributeValueForm, },
            extra_context={'object_name':_(u'attribute')}),
            name='attributes_update' ),
    url(r'^attributes/(?P<pk>\d+)/delete/$', GenericDeleteView.\
            as_view(model=ProductAttribute, success_url="attributes_list",
                    extra_context=dict(object_name=_(u'attribute'),
                    )),
            name='attributes_delete' ),
    url(r'^attributes/(?P<pk>\d+)/$', GenericDetailView.as_view(form_class=ProductAttributeForm_view,
                    template_name='attribute_form.html',
                    queryset=ProductAttribute.objects.all(),
                    inline_fields={'values': ProductAttributeValueForm_view,},
                    extra_context={'object_name':_(u'attribute'),}),
            name='attributes_view'),

    )


#eof
