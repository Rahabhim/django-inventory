# -*- encoding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from common.api import register_links, register_menu, register_submenu, user_is_staff

from models import PurchaseRequestStatus, PurchaseRequest, \
                   PurchaseRequestItem, PurchaseOrderStatus, \
                   PurchaseOrderItemStatus, PurchaseOrder, \
                   PurchaseOrderItem, Movement

from products import template_list
import procurements # just to ensure their menu is loaded before this

purchase_request_state_list = {'text':_('purchase request states'), 'view':'purchase_request_state_list', 'famfam':'pencil_go'}
purchase_request_state_create = {'text':_('create new purchase request state'), 'view':'purchase_request_state_create', 'famfam':'pencil_add', 'condition': user_is_staff}
purchase_request_state_update = {'text':_('edit state'), 'view':'purchase_request_state_update', 'args':'object.id', 'famfam':'pencil', 'condition': user_is_staff}
purchase_request_state_delete = {'text':_('delete state'), 'view':'purchase_request_state_delete', 'args':'object.id', 'famfam':'pencil_delete', 'condition': user_is_staff}

purchase_request_list = {'text':_('purchase requests'), 'view':'purchase_request_list', 'famfam':'basket_go'}
purchase_request_create = {'text':_('create new request'), 'view':'purchase_request_create', 'famfam':'basket_add'}
purchase_request_update = {'text':_('edit request'), 'view':'purchase_request_update', 'args':'object.id', 'famfam':'basket_edit'}
purchase_request_delete = {'text':_('delete request'), 'view':'purchase_request_delete', 'args':'object.id', 'famfam':'basket_delete'}
purchase_request_close = {'text':_('close request'), 'view':'purchase_request_close', 'args':'object.id', 'famfam':'cross'}
purchase_request_open = {'text':_('open request'), 'view':'purchase_request_open', 'args':'object.id', 'famfam':'accept'}
purchase_request_po_wizard = {'text':_('purchase order wizard'), 'view':'purchase_order_wizard', 'args':'object.id', 'famfam':'wand'}

purchase_request_item_create = {'text':_('add new item'), 'view':'purchase_request_item_create', 'args':'object.id', 'famfam':'basket_put'}
purchase_request_item_update = {'text':_('edit item'), 'view':'purchase_request_item_update', 'args':'object.id', 'famfam':'basket_go'}
purchase_request_item_delete = {'text':_('delete item'), 'view':'purchase_request_item_delete', 'args':'object.id', 'famfam':'basket_remove'}

purchase_order_state_list = {'text':_('purchase order states'), 'view':'purchase_order_state_list', 'famfam':'pencil_go'}
purchase_order_state_create = {'text':_('create new purchase order state'), 'view':'purchase_order_state_create', 'famfam':'pencil_add', 'condition': user_is_staff}
purchase_order_state_update = {'text':_('edit state'), 'view':'purchase_order_state_update', 'args':'object.id', 'famfam':'pencil', 'condition': user_is_staff}
purchase_order_state_delete = {'text':_('delete state'), 'view':'purchase_order_state_delete', 'args':'object.id', 'famfam':'pencil_delete', 'condition': user_is_staff}

purchase_order_item_state_list = {'text':_('purchase order item states'), 'view':'purchase_order_item_state_list', 'famfam':'pencil_go'}
purchase_order_item_state_create = {'text':_('create new item state'), 'view':'purchase_order_item_state_create', 'famfam':'pencil_add', 'condition': user_is_staff}
purchase_order_item_state_update = {'text':_('edit state'), 'view':'purchase_order_item_state_update', 'args':'object.id', 'famfam':'pencil', 'condition': user_is_staff}
purchase_order_item_state_delete = {'text':_('delete state'), 'view':'purchase_order_item_state_delete', 'args':'object.id', 'famfam':'pencil_delete', 'condition': user_is_staff}

purchase_order_list = {'text':_('purchase orders'), 'view':'purchase_order_list', 'famfam':'cart_go'}
purchase_order_create = {'text':_('create new order'), 'view':'purchase_order_create', 'famfam':'cart_add'}
purchase_order_update = {'text':_('edit order'), 'view':'purchase_order_update', 'args':'object.id', 'famfam':'pencil', 'condition': lambda o,c: o.active }
purchase_order_delete = {'text':_('delete order'), 'view':'purchase_order_delete', 'args':'object.id', 'famfam':'cart_delete', 'condition': lambda o,c: o.active }
purchase_order_close = {'text':_('close order'), 'view':'purchase_order_close', 'args':'object.id', 'famfam':'cross'}
purchase_order_open = {'text':_('open order'), 'view':'purchase_order_open', 'args':'object.id', 'famfam':'accept'}
purchase_order_receive = {'text':_('receive entire order'), 'famfam':'package_link',
            'view':'purchase_order_receive', 'args':'object.id', 
            'condition': lambda o,c: o.active }

purchase_order_item_create = {'text':_('add new item'), 'view':'purchase_order_item_create', 'args':'object.id', 'famfam':'cart_put'}
purchase_order_item_update = {'text':_('edit item'), 'view':'purchase_order_item_update', 'args':'object.id', 'famfam':'cart_go'}
purchase_order_item_delete = {'text':_('delete item'), 'view':'purchase_order_item_delete', 'args':'object.id', 'famfam':'cart_remove'}
purchase_order_item_close = {'text':_('close item'), 'view':'purchase_order_item_close', 'args':'object.id', 'famfam':'cross'}

jump_to_template = {'text':_(u'template'), 'view':'template_view', 'args':'object.item_template.id', 'famfam':'page_go'}


purchase_request_state_filter = {'name':'purchase_request_status', 'title':_(u'status'), 'queryset':PurchaseRequestStatus.objects.all(), 'destination':'status'}
purchase_order_state_filter = {'name':'purchase_order_status', 'title':_(u'status'), 'queryset':PurchaseOrderStatus.objects.all(), 'destination':'status'}
#purchase_order_active_filter = {'name':'purchase_order_active', 'title':_(u'active'), 'queryset':[True, False], 'destination':'active'}

register_links(PurchaseRequestStatus, [purchase_request_state_update, purchase_request_state_delete])
register_links(['purchase_request_state_create', 'purchase_request_state_list', 'purchase_request_state_update', 'purchase_request_state_delete'], [purchase_request_state_create], menu_name='sidebar')

register_links(PurchaseRequest, [purchase_request_update, purchase_request_delete, purchase_request_item_create, purchase_request_close, purchase_request_open, purchase_request_po_wizard])
register_links(['purchase_request_list', 'purchase_request_create', 'purchase_request_update', 'purchase_request_delete', 'purchase_request_view', 'purchase_order_wizard'], [purchase_request_create], menu_name='sidebar')

register_links(PurchaseRequestItem, [purchase_request_item_update, purchase_request_item_delete, jump_to_template])
register_links(['purchase_request_item_create'], [purchase_request_create], menu_name='sidebar')

register_links(PurchaseOrderStatus, [purchase_order_state_update, purchase_order_state_delete])
register_links(['purchase_order_state_create', 'purchase_order_state_list', 'purchase_order_state_update', 'purchase_order_state_delete'], [purchase_order_state_create], menu_name='sidebar')

register_links(PurchaseOrderItemStatus, [purchase_order_item_state_update, purchase_order_item_state_delete])
register_links(['purchase_order_item_state_create', 'purchase_order_item_state_list', 'purchase_order_item_state_update', 'purchase_order_item_state_delete'], [purchase_order_item_state_create], menu_name='sidebar')

register_links(PurchaseOrder, [dict(purchase_order_update, hide_text=True),])
register_links(['purchase_order_view',], [ purchase_order_update, purchase_order_delete, purchase_order_receive], menu_name='sidebar')
register_links(['purchase_order_list', 'purchase_order_view', 'supplier_purchase_orders'], [purchase_order_create], menu_name='sidebar')

register_links(['purchase_order_item_update'], [purchase_order_item_update, purchase_order_item_delete, jump_to_template])
register_links(['purchase_order_item_create'], [purchase_order_create], menu_name='sidebar')


register_submenu( 'menu_procurements', [ purchase_order_list,])

movement_delete = {'text':_('delete pending movement'), 'view':'movement_delete', \
            'args':'object.id', 'famfam':'basket_delete', \
            'condition': lambda o,c: o and o.state == 'draft'}

# register_submenu('menu_assets', .. )
action_destroy = dict(text=_(u'Destroy assets'), view='destroy_items', famfam='computer_delete')
action_lose = dict(text=_(u'Lose assets'), view='lose_items', famfam='computer_error')
action_move = dict(text=_(u'Move assets'), view='move_items', famfam='computer_go')

register_links( ['item_list'], [ action_destroy, action_lose, action_move ], menu_name='sidebar')
register_links(['home',], [action_destroy, action_lose, action_move ], menu_name='start_actions')
register_links(['home',], [purchase_order_create ], menu_name='start_actions')

register_links([('purchase_order_receive', Movement),], 
        [ {'text':_(u'details'), 'view':'movement_view', 'args':'object.id',
            'famfam':'page_go', 'condition': lambda o,c: o.state == 'done'},
          {'text':_(u'edit'), 'view':'movement_update_po', 'args':'object.id', 'famfam':'page_go',
           'condition': lambda o,c: o.state == 'draft'}])

movement_cart_open = {'text':_(u'Select more Items'), 'view':'movement_cart_open', 'args':'object.id', 'famfam':'package_green', 'condition': lambda o,c: o.state == 'draft'}
movement_cart_close = {'text':_(u'End selection'), 'view':'movement_cart_close', 'args':'object.id', 'famfam':'package_red', 'condition': lambda o,c: o.state == 'draft'}

register_links(['movement_view', ], [ {'text':_(u'validate move'), 'view':'movement_do_close',
            'args':'object.id', 'famfam':'page_go', 'condition': lambda o,c: o.state == 'draft'},
            movement_cart_open, movement_cart_close, movement_delete,
            ])

register_links(['movement_update_po',], [movement_delete,])

def has_pending_po(obj, context):
    all_pos = PurchaseOrder.objects.by_request(context['request']).filter(active=True)
    # We should preferrably filter 'all_pos' for those with all movements belonging
    # to our department.
    return all_pos.exists()

purchase_pending_orders = {'text':_('pending purchase orders'), \
        'condition': has_pending_po,
        'view':'purchase_order_pending_list', 'famfam':'cart_go'}

def has_pending_moves(obj, context):
    return Movement.objects.by_request(context['request']).filter(state='draft').exists()

action_movements_pending = {'text':_('pending moves'), \
        'condition': has_pending_moves,
        'view':'movements_pending_list', 'famfam':'page_go'}


register_links(['home',], [purchase_pending_orders, action_movements_pending ], menu_name='my_pending')

location_src_assets = {'text': _('assets at that location'), 'view': 'location_assets', \
            'args': dict(loc_id='object.location_src.id'), 'famfam': 'package_link'}
register_links(['movement_cart_open',], [location_src_assets,], menu_name='after_cart_open')

register_links(['purchaseorder_item_cart_open','purchaseorder_cart_open'], [template_list,], menu_name='after_cart_open')

# eof
