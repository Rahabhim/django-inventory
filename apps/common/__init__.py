# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.utils.translation import ugettext_lazy as _
from common.api import register_links, register_menu, can_add, can_edit, can_delete, user_is_staff

from models import Supplier, Location

supplier_list = {'text':_('suppliers'), 'view':'supplier_list', 'famfam':'lorry'}
supplier_create = {'text':_('create new supplier'), 'view':'supplier_create', 'famfam':'lorry_add',
            'condition': can_add(Supplier)}
supplier_update = {'text':_('edit'), 'view':'supplier_update', 'args':'object.id', 'famfam':'lorry',
            'condition': can_edit}
supplier_delete = {'text':_('delete'), 'view':'supplier_delete', 'args':'object.id', 'famfam':'lorry_delete',
            'condition': can_delete}
supplier_assign_itemtemplate = {'text':_(u'assign templates'), 'view':'supplier_assign_itemtemplates', 'args':'object.id', 'famfam':'page_go',
            'condition': can_edit}
supplier_purchase_orders = {'text':_(u'related purchase orders'), 'view':'supplier_purchase_orders', 'args':'object.id', 'famfam':'cart_go', 'condition': user_is_staff}

location_list = {'text':_('locations'), 'view':'location_list', 'famfam':'map'}
location_create = {'text':_(u'create new location'), 'view':'location_create', 'famfam':'map_add',
            'condition': can_add(Location) }
location_update = {'text':_(u'edit'), 'view':'location_update', 'args':'object.id', 'famfam':'map_edit',
            'condition': can_edit}
location_delete = {'text':_(u'delete'), 'view':'location_delete', 'args':'object.id', 'famfam':'map_delete',
            'condition': can_delete}
location_assets = {'text':_(u'assets'), 'view':'location_assets', 'args':'object.id', 'famfam':'computer', 'condition': user_is_staff}


register_links(['supplier_list', 'supplier_create', 'supplier_update', 'supplier_view', 'supplier_delete', 'supplier_assign_itemtemplates'], [supplier_create], menu_name='sidebar')
register_links(Supplier, [supplier_update, supplier_delete, supplier_assign_itemtemplate, supplier_purchase_orders])

register_links(['location_list', 'location_create', 'location_update', 'location_delete'], [location_create], menu_name='sidebar')
register_links(Location, [location_update, location_delete, location_assets])

location_filter = {'name':'location', 'title':_(u'location'), \
                'lookup_channel': 'location', 'destination':'location'}


def has_pending_inventories(obj, context):
    from inventory.models import Inventory # lazy import!
    return Inventory.objects.by_request(context['request'])\
                .filter(state__in=('draft', 'pending')).exists()

def has_no_pending_inventories(obj, context):
    """ Inverse function, prevents using a lambda
    """
    if context['user'].is_staff or context['user'].is_superuser:
        # but also unlock superusers to actions
        return True
    return not has_pending_inventories(obj, context)
#eof