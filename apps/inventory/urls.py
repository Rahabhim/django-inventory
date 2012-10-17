# -*- encoding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from django.utils.translation import ugettext_lazy as _
from django.views.generic.create_update import create_object, update_object

from generic_views.views import generic_delete, \
                                generic_detail, generic_list, \
                                GenericCreateView, GenericUpdateView

#from photos.views import generic_photos

from models import InventoryTransaction, \
                   Inventory, Log

from forms import InventoryTransactionForm, InventoryForm, \
                  LogForm, InventoryTransactionForm_inline

urlpatterns = patterns('inventory.views',
    url(r'^inventory/list/$', generic_list, dict({'queryset':Inventory.objects.all()}, extra_context=dict(title=_(u'inventories'), extra_columns=[{'name':_(u'location'), 'attribute':'location'}])), 'inventory_list'),
    url(r'^inventory/create/$', GenericCreateView.as_view(form_class=InventoryForm,
                inline_fields={'transactions': InventoryTransactionForm_inline },
                extra_context={'object_name':_(u'inventory')}), name='inventory_create'),
    url(r'^inventory/(?P<object_id>\d+)/$', 'inventory_view', (),'inventory_view'),
    url(r'^inventory/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(
                form_class=InventoryForm,
                inline_fields={'transactions': InventoryTransactionForm_inline },
                extra_context={'object_name':_(u'inventory')}), name='inventory_update'),
    url(r'^inventory/(?P<object_id>\d+)/delete/$', generic_delete, dict({'model':Inventory}, post_delete_redirect="inventory_list", extra_context=dict(object_name=_(u'inventory'))), 'inventory_delete'),
    #url(r'^inventory/(?P<object_id>\d+)/current/$', 'inventory_current', (), 'inventory_current'),
    url(r'^inventory/(?P<object_id>\d+)/transaction/create/$', 'inventory_create_transaction', (), 'inventory_create_transaction'),
    url(r'^inventory/(?P<object_id>\d+)/transaction/list/$', 'inventory_list_transactions', (), 'inventory_list_transactions'),

    url(r'^transaction/list/$', generic_list, dict({'queryset':InventoryTransaction.objects.all()}, extra_context=dict(title=_(u'transactions'))), 'inventory_transaction_list'),
    url(r'^transaction/create/$', create_object, {'model':InventoryTransaction, 'template_name':'generic_form.html', 'extra_context':{'object_name':_(u'transaction')}}, 'inventory_transaction_create'),
    url(r'^transaction/(?P<object_id>\d+)/$', generic_detail, dict(form_class=InventoryTransactionForm, queryset=InventoryTransaction.objects.all(), extra_context={'object_name':_(u'transaction')}), 'inventory_transaction_view'),
    url(r'^transaction/(?P<object_id>\d+)/update/$', update_object, {'model':InventoryTransaction, 'template_name':'generic_form.html', 'extra_context':{'object_name':_(u'transaction')}}, 'inventory_transaction_update'),
    url(r'^transaction/(?P<object_id>\d+)/delete/$', generic_delete, dict({'model':InventoryTransaction}, post_delete_redirect='inventory_list', extra_context=dict(object_name=_(u'inventory transaction'))), 'inventory_transaction_delete'),

    url(r'^supplier/(?P<object_id>\d+)/purchase/orders/$', 'supplier_purchase_orders', (), 'supplier_purchase_orders'),

#    url(r'^reports/items_per_person/(?P<object_id>\d+)/$', 'report_items_per_person', (), 'report_items_per_person'),
)


