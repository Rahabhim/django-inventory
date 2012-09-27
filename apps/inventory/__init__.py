# -*- encoding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from models import Inventory, InventoryTransaction

from common.api import register_links, register_menu

import assets


inventory_list = {'text':_('view all inventories'), 'view':'inventory_list', 'famfam':'package_go'}
inventory_create = {'text':_('create new inventory'), 'view':'inventory_create', 'famfam':'package_add'}
#inventory_balances = {'text':_(u'current balances'), 'view':'inventory_current', 'args':'object.id', 'famfam':'book_addresses'}
inventory_update = {'text':_(u'edit'), 'view':'inventory_update', 'args':'object.id', 'famfam':'package_green'}
inventory_delete = {'text':_(u'delete'), 'view':'inventory_delete', 'args':'object.id', 'famfam':'package_delete'}
inventory_create_transaction = {'text':_('add transaction'), 'view':'inventory_create_transaction', 'args':'object.id', 'famfam':'book_add'}
inventory_view = {'text':_(u'details'), 'view':'inventory_view', 'args':'object.id', 'famfam':'package_go'}
inventory_list_transactions = {'text':_(u'inventory transactions'), 'view':'inventory_list_transactions', 'args':'object.id', 'famfam':'book_go'}

inventory_transaction_list = {'text':_('view all transactions'), 'view':'inventory_transaction_list', 'famfam':'book_go'}
inventory_transaction_create = {'text':_('create new transaction'), 'view':'inventory_transaction_create', 'famfam':'book_add'}
inventory_transaction_update = {'text':_(u'edit'), 'view':'inventory_transaction_update', 'args':'object.id', 'famfam':'book_add'}
inventory_transaction_delete = {'text':_(u'delete'), 'view':'inventory_transaction_delete', 'args':'object.id', 'famfam':'book_delete'}
inventory_transaction_view = {'text':_(u'details'), 'view':'inventory_transaction_view', 'args':'object.id', 'famfam':'book_go'}

jump_to_template = {'text':_(u'template'), 'view':'template_view', 'args':'object.supply.id', 'famfam':'page_go'}
jump_to_inventory = {'text':_(u'return to inventory'), 'view':'inventory_view', 'args':'object.inventory.id', 'famfam':'package_go'}

inventory_menu_links = [
    inventory_list,#, inventory_transaction_list, inventory_transaction_create
]

register_links(['inventory_view', 'inventory_list', 'inventory_create', 'inventory_update', 'inventory_delete', 'inventory_transaction_list'], [inventory_create], menu_name='sidebar')
register_links(Inventory, [inventory_update, inventory_delete, inventory_list_transactions, inventory_create_transaction])
register_links(Inventory, [inventory_view], menu_name='sidebar')

register_links(['inventory_transaction_list', 'inventory_transaction_create', 'inventory_transaction_update', 'inventory_transaction_delete', 'inventory_transaction_view'], [inventory_create_transaction], menu_name='sidebar')
register_links(InventoryTransaction, [inventory_transaction_view, inventory_transaction_update, inventory_transaction_delete, jump_to_template])
register_links(InventoryTransaction, [jump_to_inventory], menu_name='sidebar')


register_menu([
    {'text':_('inventories'), 'view':'inventory_list', 'links':inventory_menu_links,'famfam':'package', 'position':5},
])


