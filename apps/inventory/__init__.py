# -*- encoding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from models import Inventory
# , InventoryTransaction

from common.api import register_links, register_menu, _context_has_perm

import assets
import signals

inventory_list = {'text':_('view all inventories'), 'view':'inventory_list', 'famfam':'package_go'}
inventory_create = {'text':_('create new inventory'), 'view':'inventory_create', 'famfam':'package_add'}
#inventory_balances = {'text':_(u'current balances'), 'view':'inventory_current', 'args':'object.id', 'famfam':'book_addresses'}
inventory_update = {'text':_(u'edit'), 'view':'inventory_update', 'args':'object.id', 'famfam':'package_green', 'condition': lambda o,c: not o.date_val }
inventory_delete = {'text':_(u'delete'), 'view':'inventory_delete', 'args':'object.id', 'famfam':'package_delete', 'condition': lambda o,c: not o.date_val}
inventory_view = {'text':_(u'details'), 'view':'inventory_view', 'args':'object.id', 'famfam':'package_go'}
inventory_open = {'text':_(u'open'), 'view':'inventory_open', 'args':'object.id', 'famfam':'package_green', 'condition': lambda o,c: not o.date_val}
inventory_close = {'text':_(u'close'), 'view':'inventory_close', 'args':'object.id', 'famfam':'package_red'}
inventory_compare = {'text': _(u'compare'), 'view':'inventory_items_compare', 'args':'object.id', 'famfam':'package_go',  'condition': lambda o,c: not o.date_val}

inventory_validate = {'text': _(u'validate'), 'view':'inventory_validate',
            'args':'object.id', 'famfam':'package_go',
            'condition': lambda o,c: not o.date_val}

jump_to_template = {'text':_(u'template'), 'view':'template_view', 'args':'object.supply.id', 'famfam':'page_go'}
jump_to_inventory = {'text':_(u'return to inventory'), 'view':'inventory_view', 'args':'object.inventory.id', 'famfam':'package_go'}

inventory_menu_links = [
    inventory_list,
]

register_links(['inventory_view', 'inventory_list',], [inventory_create], menu_name='sidebar')

register_links(Inventory, [inventory_update, inventory_compare])
register_links(Inventory, [inventory_delete, inventory_open, inventory_close], menu_name='sidebar')
register_links(Inventory, [inventory_view], menu_name='sidebar')
register_links(['inventory_compare', 'inventory_view'], [inventory_validate], menu_name='sidebar')

def has_pending_inventories(obj, context):
    return Inventory.objects.by_request(context['request']).filter(date_val__isnull=True).exists()

action_inventories_pending = {'text':_('pending inventories'), \
        'condition': has_pending_inventories,
        'view':'inventories_pending_list', 'famfam':'page_go'}


register_links(['home',], [action_inventories_pending ], menu_name='my_pending')

def has_inventories(o, context):
    """ Assert if current user can edit the model of `obj`
    """
    return context['user'].is_staff \
        or _context_has_perm(context, Inventory, '%(app)s.change_%(model)s') \
        or _context_has_perm(context, Inventory, '%(app)s.add_%(model)s') \
        or _context_has_perm(context, Inventory, '%(app)s.validate_inventory')

register_menu([
    {'text':_('inventories'), 'view':'inventory_list', 
        'links':inventory_menu_links,
        'famfam':'package', 'position':6,
        'condition': has_inventories},
])


