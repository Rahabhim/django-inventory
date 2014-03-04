# -*- encoding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from generic_views.views import GenericDeleteView, generic_list, \
                GenericCreateView, GenericUpdateView, GenericDetailView, \
                CartOpenView, CartCloseView, AddToCartView, RemoveFromCartView

from models import PurchaseRequestStatus, PurchaseRequest, \
                   PurchaseRequestItem, PurchaseOrderStatus, \
                   PurchaseOrderItemStatus, PurchaseOrder, \
                   PurchaseOrderItem, Movement, Supplier, \
                   RepairOrder

from movements import purchase_request_state_filter, \
                      purchase_order_state_filter


from forms import PurchaseRequestForm, PurchaseOrderForm, PurchaseOrderItemForm, \
        PurchaseOrderItemForm_inline, \
        DestroyItemsForm, LoseItemsForm, MoveItemsForm, \
        MovementForm_gu, MovementForm_view, MovementForm_update_po, MoveInternalForm, \
        RepairOrderForm_view

from procurements.models import Contract

__hush = [Contract,]

from company import make_mv_location
from main import cart_utils
import views

from views_po_wizard import PO_Wizard, PO_MassWizard

state_filter = {'name':'state', 'title': _(u'state'),
            'choices':'movements.Movement.state' , 'destination':'state'}

stype_filter = {'name':'stype', 'title':_(u'type'),
            'choices':'movements.Movement.stype' , 'destination':'stype'}


location_io_filter = {'name': 'location_src', 'title': _('Location'), 
            'destination': make_mv_location('location_src', 'location_dest')}

#def contract_filter_queryset(form, parent, parent_queryset):
#    return Contract.objects.filter(id__in=parent_queryset.order_by('procurement__id').values('procurement'))

contract_filter = {'name': 'contract', 'title':_(u'Contract'), 'lookup_channel': 'contracts',
            'destination': 'procurement'}

def supplier_filter_queryset(form, parent, parent_queryset):
    return Supplier.objects.filter(id__in=parent_queryset.order_by('supplier__id').values('supplier'))

supplier_filter = {'name': 'supplier', 'title':_(u'Supplier'),
            'queryset': supplier_filter_queryset, 'destination': 'supplier'}

po_active_filter = {'name': 'state', 'title': _(u'State'), 'destination':'state',
            'choices': 'movements.PurchaseOrder.state' }

def open_move_as_cart(obj, request):
    cart_utils.close_all_carts(request)
    cart_utils.add_cart_to_session(obj, request)
    return reverse('location_assets', kwargs=dict(loc_id=obj.location_src.id))

def check_movement(move):
    """ Check that modifications are allowed for this move
    """
    return move.state == 'draft'

def check_movement2(move):
    """ Check that this move can be deleted/rejected
    """
    return move.state in ('draft', 'pending', 'reject')

def check_repair_order(rep):
    """ Check that it is an open order
    """
    if rep.validate_user is not None:
        return False
    if rep.movements.filter(state__in=('done', 'reject')).exists():
        return False
    return True

urlpatterns = patterns('movements.views',
    url(r'^purchase/request/state/list/$', generic_list, dict({'queryset':PurchaseRequestStatus.objects.all()}, extra_context=dict(title =_(u'purchase request states'))), 'purchase_request_state_list'),
    url(r'^purchase/request/state/create/$', GenericCreateView.as_view(model=PurchaseRequestStatus, extra_context={'title':_(u'create new purchase request state')}), name='purchase_request_state_create'),
    url(r'^purchase/request/state/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(model=PurchaseRequestStatus), name='purchase_request_state_update'),
    url(r'^purchase/request/state/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(model=PurchaseRequestStatus, success_url="purchase_request_state_list", extra_context=dict(object_name=_(u'purchase request state'))), name='purchase_request_state_delete'),

    url(r'^purchase/request/list/$', generic_list, dict({'queryset':PurchaseRequest.objects.all(), 'list_filters':[purchase_request_state_filter]}, extra_context=dict(title =_(u'purchase requests'), extra_columns = [{'name':_(u'Active'), 'attribute': 'fmt_active'}])), 'purchase_request_list'),
    url(r'^purchase/request/(?P<object_id>\d+)/$', 'purchase_request_view', (), 'purchase_request_view'),
    url(r'^purchase/request/create/$', 
            GenericCreateView.as_view(form_class=PurchaseRequestForm,
                    extra_context={'title':_(u'create new purchase request')}),
            name='purchase_request_create'),
    url(r'^purchase/request/(?P<pk>\d+)/update/$', 
            GenericUpdateView.as_view( form_class=PurchaseRequestForm,),
            name='purchase_request_update'),
    url(r'^purchase/request/(?P<pk>\d+)/delete/$',
            GenericDeleteView.as_view(model=PurchaseRequest, success_url="purchase_request_list", extra_context=dict(object_name=_(u'purchase request'))), 
            name='purchase_request_delete'),
    url(r'^purchase/request/(?P<object_id>\d+)/close/$', 'purchase_request_close', (), 'purchase_request_close'),
    url(r'^purchase/request/(?P<object_id>\d+)/open/$', 'purchase_request_open', (), 'purchase_request_open'),
    url(r'^purchase/request/(?P<object_id>\d+)/purchase_order_wizard/$', 'purchase_order_wizard', (), 'purchase_order_wizard'),

    url(r'^purchase/request/(?P<object_id>\d+)/add_item/$', 'purchase_request_item_create', (), 'purchase_request_item_create'),
    url(r'^purchase/request/item/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(model=PurchaseRequestItem), name='purchase_request_item_update'),
    url(r'^purchase/request/item/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(model=PurchaseRequestItem, success_url="purchase_request_list", extra_context=dict(object_name=_(u'purchase request item'))), name='purchase_request_item_delete'),

    url(r'^purchase/order/state/list/$', generic_list, dict({'queryset':PurchaseOrderStatus.objects.all()}, extra_context=dict(title =_(u'purchase order states'))), 'purchase_order_state_list'),
    url(r'^purchase/order/state/create/$', GenericCreateView.as_view(model=PurchaseOrderStatus, extra_context={'title':_(u'create new purchase order state')}), name='purchase_order_state_create'),
    url(r'^purchase/order/state/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(model=PurchaseOrderStatus), name='purchase_order_state_update'),
    url(r'^purchase/order/state/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(model=PurchaseOrderStatus, success_url="purchase_order_state_list", extra_context=dict(object_name=_(u'purchase order status'))), name='purchase_order_state_delete'),

    url(r'^purchase/order/list/$', views.PurchaseOrderListView.as_view( \
                list_filters=[po_active_filter, contract_filter, supplier_filter]),
            name='purchase_order_list'),
    url(r'^purchase/order/pending_list/$', views.PurchaseOrderListView.as_view( \
                queryset=lambda r: PurchaseOrder.objects.by_request(r).filter(state__in=('draft', 'pending')).distinct()), 
            name='purchase_order_pending_list'),

    url(r'^purchase/order/(?P<object_id>\d+)/$', 'purchase_order_view', (), 'purchase_order_view'),
    url(r'^purchase/order/create/$', GenericCreateView.as_view(form_class=PurchaseOrderForm, 
            template_name='purchase_order_form.html',
            inline_fields={'items': PurchaseOrderItemForm_inline},
            extra_context={'title':_(u'create new purchase order')}), name='purchase_order_create'),
    url(r'^purchase/order/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(form_class=PurchaseOrderForm, 
            template_name='purchase_order_form.html',
            inline_fields={'items': PurchaseOrderItemForm_inline},
            extra_context={'title':_(u'update purchase order')}) , name='purchase_order_update'),
    url(r'^purchase/order/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(model=PurchaseOrder, success_url="purchase_order_list", extra_context=dict(object_name=_(u'purchase order'))), name='purchase_order_delete'),
    url(r'^purchase/order/(?P<object_id>\d+)/close/$', 'purchase_order_close', (), 'purchase_order_close'),
    url(r'^purchase/order/(?P<object_id>\d+)/open/$', 'purchase_order_open', (), 'purchase_order_open'),
    url(r'^purchase/order/(?P<object_id>\d+)/add_item/$', 'purchase_order_item_create', (), 'purchase_order_item_create'),
    url(r'^purchase/order/(?P<object_id>\d+)/receive/$', 'purchase_order_receive', (), 'purchase_order_receive'),
    url(r'^purchase/order/(?P<object_id>\d+)/reject/$', 'purchase_order_reject', (), 'purchase_order_reject'),
    url(r'^purchase/order/(?P<object_id>\d+)/copy/$', 'purchase_order_copy', (), 'purchase_order_copy'),

    url(r'^purchase/order/(?P<pk>\d+)/cart_open/$', views.POCartOpenView.as_view(
                dest_model='products.ItemTemplate',
                extra_context={'object_name':_(u'purchase order')}), 
            name='purchaseorder_cart_open'),
    url(r'^purchase/order/(?P<pk>\d+)/cart_close/$', CartCloseView.as_view(model=PurchaseOrder), 
            name='purchaseorder_cart_close'),

    url(r'^purchase/order/(?P<pk>\d+)/add_product/$', AddToCartView.as_view( \
                cart_model=PurchaseOrder, item_model='products.ItemTemplate'), \
            name='purchaseorder_item_add'),
    url(r'^purchase/order/(?P<pk>\d+)/remove_product/$', RemoveFromCartView.as_view(\
                cart_model=PurchaseOrder, item_model='products.ItemTemplate'), \
            name='purchaseorder_item_remove'),

    url(r'^purchase/order/item/state/list/$', generic_list, dict({'queryset':PurchaseOrderItemStatus.objects.all()}, extra_context=dict(title =_(u'purchase order item states'))), 'purchase_order_item_state_list'),
    url(r'^purchase/order/item/state/create/$',
            GenericCreateView.as_view(model=PurchaseOrderItemStatus, extra_context={'title':_(u'create new purchase order item state')}), 
            name='purchase_order_item_state_create'),
    url(r'^purchase/order/item/state/(?P<pk>\d+)/update/$',
            GenericUpdateView.as_view(model=PurchaseOrderItemStatus),
            name='purchase_order_item_state_update'),
    url(r'^purchase/order/item/state/(?P<pk>\d+)/delete/$',
            GenericDeleteView.as_view(model=PurchaseOrderItemStatus, success_url="purchase_order_item_state_list", extra_context=dict(object_name=_(u'purchase order item status'))), 
            name='purchase_order_item_state_delete'),

    url(r'^purchase/order/item/(?P<pk>\d+)/update/$',
            GenericUpdateView.as_view(form_class=PurchaseOrderItemForm),
            name='purchase_order_item_update'),
    url(r'^purchase/order/item/(?P<pk>\d+)/delete/$',
            GenericDeleteView.as_view(model=PurchaseOrderItem, success_url="purchase_order_list", extra_context=dict(object_name=_(u'purchase order item'))),
            name='purchase_order_item_delete'),
    url(r'^purchase/order/item/(?P<object_id>\d+)/close/$', 'purchase_order_item_close', (), 'purchase_order_item_close'),

    url(r'^purchase/order/item/(?P<pk>\d+)/cart_open/$', views.POItemCartOpenView.as_view(
                dest_model='products.ItemTemplate',
                extra_context={'object_name':_(u'purchase order item')}), 
            name='purchaseorder_item_cart_open'),
    url(r'^purchase/order/item/(?P<pk>\d+)/cart_close/$', CartCloseView.as_view(model=PurchaseOrderItem), 
            name='purchaseorder_item_cart_close'),

    url(r'^purchase/order/item/(?P<pk>\d+)/add_product/$', views.POIAddMainView.as_view( \
                item_model='products.ItemTemplate'), \
            name='purchaseorder_item_product_add'),
    url(r'^purchase/order/item/(?P<pk>\d+)/add_bundled/$', views.POIAddBundledView.as_view( \
                item_model='products.ItemTemplate'), \
            name='purchaseorder_item_bundled_add'),

    url(r'^objects/items/destroy/$', GenericCreateView.as_view(form_class=DestroyItemsForm, 
            template_name="destroy_form.html",
            extra_context={'title':_(u'Items destruction')},
            success_url=open_move_as_cart),
        name='destroy_items'),

    url(r'^objects/items/lose/$', GenericCreateView.as_view(form_class=LoseItemsForm, 
            template_name="lose_form.html",
            extra_context={'title':_(u'Lost Items')},
            success_url=open_move_as_cart),
        name='lose_items'),

    url(r'^objects/items/move/$', GenericCreateView.as_view(form_class=MoveItemsForm, 
            template_name="movement_form.html",
            extra_context={'title':_(u'Items movement')},
            success_url=open_move_as_cart),
        name='move_items'),

    url(r'^objects/items/move_internal/$', GenericCreateView.as_view(form_class=MoveInternalForm, 
            template_name="movement_form.html",
            extra_context={'title':_(u'Items internal movement')},
            success_url=open_move_as_cart),
        name='move_items_internal'),
    url(r'^objects/moves/list/$', views.MovementListView.as_view( \
                    list_filters=[state_filter, stype_filter, \
                                location_io_filter],),
            name='movements_list'),
    url(r'^objects/moves/pending_list/$', views.MovementListView.as_view( \
                    queryset=lambda r: Movement.objects.by_request(r).filter(state__in=('draft', 'pending')).exclude(stype='in'),
                    list_filters=[ stype_filter, \
                                location_io_filter],),
            name='movements_pending_list'),
    url(r'^objects/moves/(?P<pk>\d+)/$', GenericDetailView.as_view(
                form_class=MovementForm_view,
                template_name='movement_form.html',
                queryset=Movement.objects.all(),
                ),
            name='movement_view'),
    url(r'^objects/moves/(?P<pk>\d+)/update/$', GenericUpdateView.as_view( \
                template_name="movement_form_gu.html",
                queryset=Movement.objects.by_request,
                check_object=check_movement,
                form_class=MovementForm_gu,
            ),
            name='movement_update_generic'),
    url(r'^objects/moves/(?P<pk>\d+)/update_po/$', GenericUpdateView.as_view( \
                template_name="movement_form.html",
                check_object=check_movement,
                queryset=Movement.objects.by_request,
                form_class=MovementForm_update_po,
                success_url=lambda obj, *a: reverse('purchase_order_receive', kwargs=dict(object_id=obj.purchase_order.id)),
            ),
            name='movement_update_po'),

    url(r'^objects/moves/(?P<object_id>\d+)/close/$', 'movement_do_close',
            name='movement_do_close'),

    url(r'^objects/moves/(?P<object_id>\d+)/reject/$', 'movement_do_reject',
            name='movement_do_reject'),

    url(r'^objects/moves/(?P<pk>\d+)/cart_open/$', CartOpenView.as_view(
                model=Movement, dest_model='assets.Item', exclusive=True,
                check_object=check_movement,
                extra_context={'title':_(u'add items to movement')}),
            name='movement_cart_open'),
    url(r'^objects/moves/(?P<pk>\d+)/cart_close/$', CartCloseView.as_view(model=Movement), 
            name='movement_cart_close'),

    url(r'^objects/moves/(?P<pk>\d+)/add_item/$', AddToCartView.as_view( \
                cart_model=Movement, item_model='assets.Item'), \
            name='movement_item_add'),
    url(r'^objects/moves/(?P<pk>\d+)/remove_item/$', RemoveFromCartView.as_view(\
                cart_model=Movement, item_model='assets.Item'), \
            name='movement_item_remove'),

    url(r'^objects/moves/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(model=Movement, success_url="movements_pending_list", 
                check_object=check_movement2,
                queryset=Movement.objects.by_request,
                extra_context=dict(object_name=_(u'Movement'))), name='movement_delete'),

    url(r'^po/wizard/$', PO_Wizard.as_view(), name="purchaseorder_wizard" ),
    url(r'^po/wizard/new/$', PO_Wizard.as_view(), kwargs={'new': True}, name="purchaseorder_wizard_new" ),
    url(r'^po/wizard/(?P<object_id>\d+)/$', PO_Wizard.as_view(), name="purchaseorder_wizard_update" ),

    url(r'^po/mass-wizard/$', PO_MassWizard.as_view(), name="purchaseorder_wizard_mass" ),
    url(r'^po/mass-wizard/new/$', PO_MassWizard.as_view(), kwargs={'new': True}, name="purchaseorder_wizard_new_mass" ),
    url(r'^po/mass-wizard/(?P<object_id>\d+)/$', PO_MassWizard.as_view(), name="purchaseorder_wizard_update_mass" ),

    # Repair Orders
    url(r'^itemgroup/(?P<object_id>\d+)/repair/$', 'repair_itemgroup',
            name='repair_itemgroup'),

    url(r'^objects/repair/(?P<pk>\d+)/$', GenericDetailView.as_view(
                form_class=RepairOrderForm_view,
                template_name='repair_order_form.html',
                queryset=RepairOrder.objects.by_request,
                extra_fields= [{'field':'movements.all', 'label':_(u'Movements')}, ],
                extra_context={'title': _(u'repair order details') },
                ),
            name='repair_order_view'),
    url(r'^objects/repair/list/$', views.RepairOrderListView.as_view( \
                    list_filters=[],),
            name='repair_order_list'),
    url(r'^objects/repair/pending_list/$', views.RepairOrderListView.as_view( \
                    queryset=lambda r: RepairOrder.objects.by_request(r).filter(state__in=('draft', 'pending')),
                    list_filters=[],),
            name='repair_pending_list'),
    url(r'^objects/repair/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(
                model=RepairOrder, success_url="repair_order_list",
                queryset=RepairOrder.objects.by_request,
                check_object=check_repair_order,
                extra_context=dict(object_name=_(u'Repair Order'))),
            name='repair_order_delete'),
    url(r'^objects/repair/(?P<object_id>\d+)/close/$', 'repair_do_close',
            name='repair_do_close'),

)

#eof
