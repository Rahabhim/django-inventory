# -*- encoding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from django.utils.translation import ugettext_lazy as _

from generic_views.views import GenericDeleteView, \
                                generic_detail, generic_list, \
                                GenericCreateView, GenericUpdateView, \
                                CartOpenView, CartCloseView, AddToCartView, RemoveFromCartView

from models import Inventory, InventoryItem, Log

from forms import InventoryForm, InventoryItemForm, \
                 LogForm, InventoryItemForm_inline

urlpatterns = patterns('inventory.views',
    url(r'^inventory/list/$', generic_list, dict({'queryset':Inventory.objects.by_request}, 
                extra_context=dict(title=_(u'inventories'), 
                extra_columns=[{'name':_(u'location'), 'attribute':'location'}])),
                'inventory_list'),
    url(r'^inventory/pending_list/$', generic_list, dict({'queryset':lambda r: Inventory.objects.by_request(r).filter(date_val__isnull=True)}, 
                extra_context=dict(title=_(u'pending inventories'), 
                extra_columns=[{'name':_(u'location'), 'attribute':'location'}])),
                'inventories_pending_list'),
    url(r'^inventory/create/$', GenericCreateView.as_view(form_class=InventoryForm,
                inline_fields={'items': InventoryItemForm_inline },
                extra_context={'object_name':_(u'inventory')}), name='inventory_create'),
    url(r'^inventory/(?P<object_id>\d+)/$', 'inventory_view', (),'inventory_view'),
    url(r'^inventory/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(
                form_class=InventoryForm,
                inline_fields={'items': InventoryItemForm_inline },
                extra_context={'object_name':_(u'inventory')}), name='inventory_update'),
    url(r'^inventory/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(model=Inventory,
                success_url="inventory_list", 
                extra_context=dict(object_name=_(u'inventory'))), name='inventory_delete'),
    url(r'^inventory/(?P<pk>\d+)/open/$', CartOpenView.as_view(
                model=Inventory, dest_model='assets.Item',
                extra_context={'object_name':_(u'inventory')}), name='inventory_open'),
    url(r'^inventory/(?P<pk>\d+)/close/$', CartCloseView.as_view(model=Inventory), name='inventory_close'),
    #url(r'^inventory/(?P<object_id>\d+)/current/$', 'inventory_current', (), 'inventory_current'),

    url(r'^inventory/(?P<object_id>\d+)/compare/$', 'inventory_items_compare', (), 'inventory_items_compare'),
    url(r'^inventory/(?P<object_id>\d+)/validate/$', 'inventory_validate', (), 'inventory_validate'),
    url(r'^inventory_item/list/$', generic_list, dict(queryset=InventoryItem.objects.all(), 
                extra_context=dict(title=_(u'items'))), 'inventory_item_list'),
    
    url(r'^inventory_item/(?P<object_id>\d+)/$', generic_detail, dict(form_class=InventoryItemForm, 
                queryset=InventoryItem.objects.all(),
                extra_context={'object_name':_(u'inventory item')}), 'inventory_item_view'),

    url(r'^supplier/(?P<object_id>\d+)/purchase/orders/$', 'supplier_purchase_orders', (), 'supplier_purchase_orders'),

    # TODO: validate..
    url(r'^inventory/(?P<pk>\d+)/add_item/$', AddToCartView.as_view( \
                cart_model=Inventory, item_model='assets.Item'), \
            name='inventory_item_add'),
    url(r'^inventory/(?P<pk>\d+)/remove_item/$', RemoveFromCartView.as_view(\
                cart_model=Inventory, item_model='assets.Item'), \
            name='inventory_item_remove'),
)


#eof