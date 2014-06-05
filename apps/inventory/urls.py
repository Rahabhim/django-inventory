# -*- encoding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from django.utils.translation import ugettext_lazy as _

from generic_views.views import GenericDeleteView, \
                                generic_detail, generic_list, \
                                GenericBloatedListView, \
                                GenericCreateView, GenericUpdateView, \
                                CartOpenView, CartCloseView, AddToCartView, RemoveFromCartView

from models import Inventory, InventoryGroup, InventoryItem

from company.models import Department
from company.lookups import _department_filter_q
from common.api import user_is_staff
from django.db.models import Q

from forms import InventoryForm, InventoryItemForm, \
                 InventoryItemForm_inline

def check_inventory(inventory):
    """ Check that it is an open inventory
    """
    return inventory.date_val is None and inventory.validate_user is None

inv_name_filter = {'name': 'name', 'title': _('name'), 'destination': 'name'}

inv_state_filter = {'name':'state', 'title': _(u'state'),
            'choices':'inventory.InventoryGroup.state' , 'destination':'state'}

inv_department_filter = {'name': 'dept', 'title': _('department'),
            'condition': user_is_staff,
            'destination': lambda q: Q(department__in=Department.objects.filter(_department_filter_q(q))) }

urlpatterns = patterns('inventory.views',
    url(r'^inventory/list/$', GenericBloatedListView.as_view(queryset=InventoryGroup.objects.by_request,
                list_filters=[inv_name_filter, inv_state_filter, inv_department_filter],
                extra_context=dict(title=_(u'inventories'),
                extra_columns=[{'name':_(u'department'), 'attribute':'department'},
                        {'name': _('state'), 'attribute': 'get_state_display', 'order_attribute': 'state'}])),
                name='inventory_list'),
    url(r'^inventory/pending_list/$', generic_list, dict({
                    'queryset': lambda r: InventoryGroup.objects.by_request(r)\
                            .filter(state__in=('draft', 'pending'))}, 
                extra_context=dict(title=_(u'pending inventories'), 
                extra_columns=[{'name':_(u'department'), 'attribute':'department'},
                        {'name': _('state'), 'attribute': 'get_state_display'}])),
                'inventories_pending_list'),
    url(r'^inventory/pending2_list/$', generic_list, dict({
                    'queryset': lambda r: InventoryGroup.objects.by_request(r)\
                            .filter(state='pending')}, 
                extra_context=dict(title=_(u'inventories pending validation'), 
                extra_columns=[{'name':_(u'department'), 'attribute':'department'},
                        {'name': _('state'), 'attribute': 'get_state_display'}])),
                'inventories_pending2_list'),
    url(r'^inventory/create/$', GenericCreateView.as_view(form_class=InventoryForm,
                template_name="inventory_create.html",
                extra_context={'title':_(u'open new inventory')}), name='inventory_create'),
    url(r'^inventory/(?P<object_id>\d+)/$', 'inventory_view', (),'inventory_view'),
    url(r'^inventory/g/(?P<object_id>\d+)/$', 'inventory_group_view', (),'inventory_group_view'),
    url(r'^inventory/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(
                form_class=InventoryForm, check_object=check_inventory,
                inline_fields={'items': InventoryItemForm_inline },
                extra_context={'object_name':_(u'inventory')}), name='inventory_update'),
    url(r'^inventory/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(model=InventoryGroup,
                success_url="inventory_list", check_object=check_inventory,
                extra_context=dict(object_name=_(u'inventory'))), name='inventory_delete'),
    url(r'^inventory/(?P<pk>\d+)/open/$', CartOpenView.as_view(
                model=InventoryGroup, dest_model='assets.Item', check_object=check_inventory,
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

    url(r'^inventory/(?P<pk>\d+)/add_item/$', AddToCartView.as_view( \
                cart_model=InventoryGroup, item_model='assets.Item'), \
            name='inventory_item_add'),
    url(r'^inventory/(?P<pk>\d+)/remove_item/$', RemoveFromCartView.as_view(\
                cart_model=InventoryGroup, item_model='assets.Item'), \
            name='inventory_item_remove'),
    url(r'^inventory/(?P<object_id>\d+)/inventory.pdf$', 'inventory_printout', \
            name='inventory_printout'),
    url(r'^inventory/(?P<object_id>\d+)/reject/$', 'inventory_reject', name='inventory_reject'),
)


#eof