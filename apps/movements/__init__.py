# -*- encoding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from common import has_pending_inventories, has_no_pending_inventories
from common.api import register_links, register_menu, register_submenu, \
                    role_from_request, \
                    can_add, user_is_staff, _context_has_perm, can_edit, can_delete

from models import PurchaseRequestStatus, PurchaseRequest, \
                   PurchaseRequestItem, PurchaseOrderStatus, \
                   PurchaseOrderItemStatus, PurchaseOrder, \
                   PurchaseOrderItem, Movement, RepairOrder

from products import template_list
import procurements # just to ensure their menu is loaded before this

def iz_open(obj, context):
    return obj.state in ('draft', 'pending')

def iz_open_or_rej(obj, context):
    return obj.state in ('draft', 'pending', 'reject')

def iz_single_dept(obj, context):
    if context['request'].user.is_staff or obj.department is not None:
        return True
    else:
        return False

def check_our_move(state=None, perm=False):
    """ Check if movement is for our active role's department and has some state
    """
    if isinstance(state, basestring):
        state = (state, )

    def __check(move, context):
        if (state is not None) and (move.state not in state):
            return False
        if perm and not _context_has_perm(context, Movement, perm):
            return False
        if context['request'].user.is_staff:
            return True
        else:
            rrq = role_from_request(context['request'])
            if rrq and (rrq.department == (move.location_src.department or move.location_dest.department or "foo bar")):
                return True
        return False

    return __check

def can_do_mass_po(o,c):
    cnt = 0
    if c['request'].user.is_staff:
        return True
    for dr in c['request'].user.dept_roles.all():
        if dr.has_perm('movements.add_purchaseorder'):
            cnt += 1
    if cnt >= 10:
        return True
    return False


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
purchase_order_create = {'text':_('create new order'), 'view':'purchase_order_create', 'famfam':'cart_add', 'condition': can_add(PurchaseOrder)}
purchase_order_update = {'text':_('edit order'), 'view':'purchase_order_update', 'args':'object.id', 'famfam':'pencil', 'condition': lambda o,c: o.state }

purchase_order_updwiz = {'text':_('edit order items'), 'view':'purchaseorder_wizard_update', 'args':'object.id', 'famfam':'pencil', 'condition': (iz_open, iz_single_dept,  can_edit, has_no_pending_inventories)  }
purchase_order_updwiz_mass = {'text':_('edit order items (mass)'), 
            'view':'purchaseorder_wizard_update_mass', 'args':'object.id', 'famfam':'pencil',
            'condition': (iz_open, lambda o,c: o.department is None, can_do_mass_po, can_edit, has_no_pending_inventories)  }
purchase_order_delete = {'text':_('delete order'), 'view':'purchase_order_delete', 'args':'object.id', 'famfam':'cart_delete', 'condition': (iz_open_or_rej, can_delete)  }
purchase_order_close = {'text':_('close order'), 'view':'purchase_order_close', 'args':'object.id', 'famfam':'cross'}
purchase_order_open = {'text':_('open order'), 'view':'purchase_order_open', 'args':'object.id', 'famfam':'accept'}
purchase_order_receive = {'text':_('receive entire order'), 'famfam':'package_link',
            'view':'purchase_order_receive', 'args':'object.id', 
            'condition': (iz_open, lambda o,c: _context_has_perm(c, PurchaseOrder, '%(app)s.receive_%(model)s'))  }

purchase_order_wizard = {'text':_('create new order'), 'view':'purchaseorder_wizard_new', 'famfam':'cart_add', 
            'condition': (can_add(PurchaseOrder), has_no_pending_inventories)}

purchase_order_wizard_mass = {'text':_('create new mass order'), 'view':'purchaseorder_wizard_new_mass', 'famfam':'cart_add', 
            'condition': (can_do_mass_po, has_no_pending_inventories)}

purchase_order_reject = {'text':_('reject order'), 'famfam':'package_red',
            'view':'purchase_order_reject', 'args':'object.id', 
            'condition': (iz_open, lambda o,c: _context_has_perm(c, PurchaseOrder, '%(app)s.validate_%(model)s'))  }

purchase_order_copy = {'text':_('copy order'), 'famfam':'table_multiple',
            'view':'purchase_order_copy', 'args':'object.id',
            'condition': (can_do_mass_po, has_no_pending_inventories)  }

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

register_links(PurchaseOrder, [dict(purchase_order_updwiz, hide_text=True), dict(purchase_order_updwiz_mass, hide_text=True)])
register_links(['purchase_order_view',], [purchase_order_receive, purchase_order_reject,  purchase_order_delete, purchase_order_copy], menu_name='sidebar')
# register_links(['purchase_order_list', 'purchase_order_view', 'supplier_purchase_orders'], [purchase_order_create], menu_name='sidebar')

register_links(['purchase_order_item_update'], [purchase_order_item_update, purchase_order_item_delete, jump_to_template])
#register_links(['purchase_order_item_create'], [purchase_order_create], menu_name='sidebar')


register_submenu( 'menu_procurements', [ purchase_order_list,])

def can_delete_movement(obj, context):
    if not Movement.objects.by_request(context['request']).filter(id=obj.id).exists():
        return False
    if _context_has_perm(context, obj, '%(app)s.delete_%(model)s'):
        return True
    elif obj.stype == 'in' and _context_has_perm(context, obj, '%(app)s.delete_in_%(model)s'):
        return True
    else:
        return False

movement_delete = {'text':_('delete pending movement'), 'view':'movement_delete', \
            'args':'object.id', 'famfam':'basket_delete', \
            'condition': (iz_open_or_rej, can_delete_movement) }

# register_submenu('menu_assets', .. )
action_destroy = dict(text=_(u'Destroy assets'), view='destroy_items', famfam='computer_delete', condition= (can_add(Movement), has_no_pending_inventories))
action_lose = dict(text=_(u'Lose assets'), view='lose_items', famfam='computer_error', condition= (can_add(Movement), has_no_pending_inventories))
action_move = dict(text=_(u'Move assets'), view='move_items', famfam='computer_go', condition= (can_add(Movement), has_no_pending_inventories))
action_move_internal = dict(text=_(u'Move assets (internal)'), view='move_items_internal', famfam='computer_go', condition= (can_add(Movement), has_no_pending_inventories))

register_links( ['item_list'], [ action_destroy, action_lose, action_move, action_move_internal ], menu_name='sidebar')
register_links(['home',], [action_destroy, action_lose, action_move, action_move_internal ], menu_name='start_actions')
register_links(['home',], [purchase_order_wizard, purchase_order_wizard_mass ], menu_name='start_actions')

register_links([('purchase_order_receive', Movement),], 
        [ {'text':_(u'details'), 'view':'movement_view', 'args':'object.id',
            'famfam':'page_go', 'condition': (check_our_move(state='done'), has_no_pending_inventories)},
          {'text':_(u'edit'), 'view':'movement_update_po', 'args':'object.id', 'famfam':'page_go',
           'condition': check_our_move(state=('draft', 'pending')) }])

movement_cart_open = {'text':_(u'Select more Items'), 'view':'movement_cart_open',
            'args':'object.id', 'famfam':'package_green',
            'condition': (check_our_move(state='draft'),  can_edit, has_no_pending_inventories) }
movement_cart_close = {'text':_(u'End selection'), 'view':'movement_cart_close',
            'args':'object.id', 'famfam':'package_red',
            'condition': check_our_move(state='draft', perm='%(app)s.change_%(model)s')}

movement_validate = {'text':_(u'validate move'), 'view':'movement_do_close',
            'args':'object.id', 'famfam':'page_go', 
            'condition': check_our_move(state=('draft', 'pending'), perm='%(app)s.validate_%(model)s') }

movement_reject = {'text':_(u'reject move'), 'view':'movement_do_reject',
            'args':'object.id', 'famfam':'alert', 
            'condition': check_our_move(state=('draft', 'pending'), perm='%(app)s.validate_%(model)s') }

register_links(['movement_view', ], [ movement_validate, movement_reject,
            movement_cart_open, movement_cart_close, movement_delete,
            ])

register_links(['movement_update_po',], [movement_delete,])

def has_pending_po(obj, context):
    if has_pending_inventories(None, context):
        return False
    all_pos = PurchaseOrder.objects.by_request(context['request']).filter(state__in=('draft', 'pending'))
    # We should preferrably filter 'all_pos' for those with all movements belonging
    # to our department.
    return all_pos.exists()

purchase_pending_orders = {'text':_('pending purchase orders'), \
        'condition': has_pending_po,
        'view':'purchase_order_pending_list', 'famfam':'cart_go'}

def has_pending_moves(obj, context):
    if has_pending_inventories(None, context):
        return False
    return Movement.objects.by_request(context['request']).filter(state__in=('draft', 'pending')) \
                .exclude(stype='in').exists()

action_movements_pending = {'text':_('pending moves'), \
        'condition': has_pending_moves,
        'view':'movements_pending_list', 'famfam':'page_go'}

# Repair Orders

def iz_itemgroup(item, c):
    from assets.models import ItemGroup
    if isinstance(item, ItemGroup):
        return True
    try:
        # if it's a plain item, we'll get an exception
        if item.itemgroup is not None:
            return True
    except ItemGroup.DoesNotExist:
        return False

action_repair_itemgroup = {'text': _("Repair bundle"), 'view': 'repair_itemgroup', 'args': 'object.id',
        'famfam': 'wrench_orange', 'condition': (can_edit, has_no_pending_inventories, iz_itemgroup)}

register_links(['group_view',], [action_repair_itemgroup,])
repair_order_list = {'text':_('repair orders'), 'view':'repair_order_list', 'famfam':'wrench'}

def has_pending_repairs(obj, context):
    if has_pending_inventories(None, context):
        return False
    return RepairOrder.objects.by_request(context['request']).filter(state__in=('draft', 'pending')).exists()

action_repairs_pending = {'text':_('pending repairs'), \
        'condition': has_pending_repairs,
        'view':'repair_pending_list', 'famfam':'wrench_orange'}

action_repair_validate = {'text':_(u'validate repair'), 'view':'repair_do_close',
            'args':'object.id', 'famfam':'page_go', 'condition': lambda o,c: o.state in ('draft', 'pending') and _context_has_perm(c, RepairOrder, '%(app)s.validate_%(model)s') }

action_repair_delete = {'text':_('delete pending repair'), 'view':'repair_order_delete', \
            'args':'object.id', 'famfam':'table_delete', \
            'condition': lambda o,c: o and o.state in ('draft', 'pending') }

register_links(['repair_order_view', ], [ action_repair_delete, action_repair_validate ])

register_links(['home',], [purchase_pending_orders, action_movements_pending, action_repairs_pending ], \
            menu_name='my_pending')

location_src_assets = {'text': _('assets at that location'), 'view': 'location_assets', \
            'args': dict(loc_id='object.location_src.id'), 'famfam': 'package_link'}
register_links(['movement_cart_open',], [location_src_assets,], menu_name='after_cart_open')

register_links(['purchaseorder_item_cart_open','purchaseorder_cart_open'], [template_list,], menu_name='after_cart_open')

# eof
