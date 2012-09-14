# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.utils.translation import ugettext_lazy as _
from common.api import register_links, register_menu

from models import Supplier, Location

supplier_create = {'text':_('create new supplier'), 'view':'supplier_create', 'famfam':'lorry_add'}
supplier_list = {'text':_('suppliers'), 'view':'supplier_list', 'famfam':'lorry'}
supplier_update = {'text':_('edit'), 'view':'supplier_update', 'args':'object.id', 'famfam':'lorry'}
supplier_delete = {'text':_('delete'), 'view':'supplier_delete', 'args':'object.id', 'famfam':'lorry_delete'}
supplier_assign_itemtemplate = {'text':_(u'assign templates'), 'view':'supplier_assign_itemtemplates', 'args':'object.id', 'famfam':'page_go'}
supplier_purchase_orders = {'text':_(u'related purchase orders'), 'view':'supplier_purchase_orders', 'args':'object.id', 'famfam':'cart_go'}

location_list = {'text':_('locations'), 'view':'location_list', 'famfam':'map'}
location_create = {'text':_(u'create new location'), 'view':'location_create', 'famfam':'map_add'}
location_update = {'text':_(u'edit'), 'view':'location_update', 'args':'object.id', 'famfam':'map_edit'}
location_delete = {'text':_(u'delete'), 'view':'location_delete', 'args':'object.id', 'famfam':'map_delete'}


register_links(['supplier_list', 'supplier_create', 'supplier_update', 'supplier_view', 'supplier_delete', 'supplier_assign_itemtemplates'], [supplier_create], menu_name='sidebar')
register_links(Supplier, [supplier_update, supplier_delete, supplier_assign_itemtemplate, supplier_purchase_orders])

register_links(['location_list', 'location_create', 'location_update', 'location_delete'], [location_create], menu_name='sidebar')
register_links(Location, [location_update, location_delete])

location_filter = {'name':'location', 'title':_(u'location'), 'queryset':Location.objects.all(), 'destination':'location'}


#eof