# -*- encoding: utf-8 -*-
import datetime
from collections import defaultdict

from django import forms
from django.utils.translation import ugettext_lazy as _
#from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
#from django.contrib.contenttypes.models import ContentType
#from django.views.generic.list_detail import object_detail, object_list
from django.core.urlresolvers import reverse
#from django.views.generic.create_update import create_object
from django.forms.formsets import formset_factory

from common.models import Supplier, Location
from common.api import role_from_request
from assets.models import ItemTemplate, Item, ItemGroup
from generic_views.views import GenericBloatedListView, CartOpenView, _ModifyCartView
from main import cart_utils

from models import PurchaseRequest, PurchaseRequestItem, PurchaseOrder, \
                    Movement, RepairOrder
from forms import PurchaseRequestForm_view, PurchaseRequestItemForm, \
                  PurchaseOrderForm_view, PurchaseOrderItemForm, \
                  PurchaseOrderItem, PurchaseOrderWizardItemForm, \
                  PurchaseOrderForm_short_view


def purchase_request_view(request, object_id):
    purchase_request = get_object_or_404(PurchaseRequest, pk=object_id)
    form = PurchaseRequestForm_view(
        instance=purchase_request,
        extra_fields=[
            {'field':'purchaseorder_set.all', 'label':_(u'Related purchase orders')}
        ]
    )

    return render_to_response('generic_detail.html', {
        'title':_(u'details for purchase request: %s') % purchase_request,
        'object':purchase_request,
        'form':form,
        'subtemplates_dict':[
            {
            'name':'generic_list_subtemplate.html',
            'title':_(u'purchase request items'),
            'object_list':purchase_request.purchaserequestitem_set.all(),
            'extra_columns':[{'name':_(u'qty'), 'attribute':'qty'}],
            },
            #TODO: Used this instead when pagination namespace is supported
            #{
            #    'name':'generic_list_subtemplate.html',
            #    'title':_(u'related purchase orders'),
            #    'object_list':purchase_request.purchaseorder_set.all(),
            #    'extra_columns':[{'name':_(u'issue data'), 'attribute':'issue_date'}],
            #}
        ]
    },
    context_instance=RequestContext(request))


def purchase_request_item_create(request, object_id):
    purchase_request = get_object_or_404(PurchaseRequest, pk=object_id)

    if request.method == 'POST':
        form = PurchaseRequestItemForm(request.POST)#, initial={'purchase_request':purchase_request})
        if form.is_valid():
            form.save()
            msg = _(u'The purchase request item was created successfully.')
            messages.success(request, msg, fail_silently=True)
            return redirect(purchase_request.get_absolute_url())
    else:
        form = PurchaseRequestItemForm(initial={'purchase_request':purchase_request})

    return render_to_response('generic_form.html', {
        'form':form,
        'title': _(u'add new purchase request item') ,
    },
    context_instance=RequestContext(request))


def purchase_request_close(request, object_id):
    purchase_request = get_object_or_404(PurchaseRequest, pk=object_id)

    data = {
        'object':purchase_request,
        'title': _(u"Are you sure you wish to close the purchase request: %s?") % purchase_request,
    }

    if purchase_request.active == False:
        msg = _(u'This purchase request has already been closed.')
        messages.error(request, msg, fail_silently=True)
        return redirect(request.META['HTTP_REFERER'] if 'HTTP_REFERER' in request.META else purchase_request.get_absolute_url())

    if request.method == 'POST':
        purchase_request.active = False
        purchase_request.save()
        msg = _(u'The purchase request has been closed successfully.')
        messages.success(request, msg, fail_silently=True)
        return redirect(purchase_request.get_absolute_url())

    return render_to_response('generic_confirm.html', data,
    context_instance=RequestContext(request))


def purchase_request_open(request, object_id):
    purchase_request = get_object_or_404(PurchaseRequest, pk=object_id)

    data = {
        'object':purchase_request,
        'title':_(u"Are you sure you wish to open the purchase request: %s?") % purchase_request,
    }

    if purchase_request.active == True:
        msg = _(u'This purchase request is already open.')
        messages.error(request, msg, fail_silently=True)
        return redirect(request.META['HTTP_REFERER'] if 'HTTP_REFERER' in request.META else purchase_request.get_absolute_url())

    if request.method == 'POST':
        purchase_request.active = True
        purchase_request.save()
        msg = _(u'The purchase request has been opened successfully.')
        messages.success(request, msg, fail_silently=True)
        return redirect(purchase_request.get_absolute_url())

    return render_to_response('generic_confirm.html', data,
    context_instance=RequestContext(request))



def purchase_order_wizard(request, object_id):
    """
    Creates new purchase orders based on the item suppliers selected
    from a purchase request
    """

    purchase_request = get_object_or_404(PurchaseRequest, pk=object_id)

    #A closed purchase orders may also mean a PO has been generated
    # previously from it by this wizard
    if purchase_request.active == False:
        msg = _(u'This purchase request is closed.')
        messages.error(request, msg, fail_silently=True)
        return redirect(request.META['HTTP_REFERER'] if 'HTTP_REFERER' in request.META else purchase_request.get_absolute_url())

    if not purchase_request.purchaserequestitem_set.all():
        msg = _(u'This purchase request is empty, add items before using the wizard.')
        messages.error(request, msg, fail_silently=True)
        return redirect(request.META['HTTP_REFERER'] if 'HTTP_REFERER' in request.META else purchase_request.get_absolute_url())


    #Create a formset for all the items in the purchase request
    #and let the user select from the available suppliers from each
    #item
    ItemsFormSet = formset_factory(PurchaseOrderWizardItemForm, extra=0)

    initial = []
    for item in purchase_request.purchaserequestitem_set.all():
        initial.append({
            'item':item
        })

    if request.method == 'POST':
        formset = ItemsFormSet(request.POST, initial=initial)
        if formset.is_valid():
            #Create a dictionary of supplier and corresponding items
            #to be ordered from them
            #TODO: Can this be done with a reduce function?
            suppliers = {}
            for form in formset.forms:
                supplier = get_object_or_404(Supplier, pk=form.cleaned_data['supplier'])
                item_template = get_object_or_404(ItemTemplate, pk=form.cleaned_data['template_id'])
                if supplier in suppliers:
                    suppliers[supplier].append({'item_template':item_template, 'qty': form.cleaned_data['qty']})
                else:
                    suppliers[supplier] = [{'item_template':item_template, 'qty': form.cleaned_data['qty']}]

            #Create a new purchase order for each supplier in the
            #suppliers directory
            new_pos = []
            for supplier, po_items_data in suppliers.items():
                purchase_order = PurchaseOrder(
                    purchase_request=purchase_request,
                    supplier=supplier
                )
                new_pos.append(purchase_order)
                purchase_order.save()

                #Create the purchase order items
                for po_item_data in po_items_data:
                    po_item = PurchaseOrderItem(
                        purchase_order=purchase_order,
                        item_template=po_item_data['item_template'],
                        qty=po_item_data['qty']
                    )
                    po_item.save()

            purchase_request.active = False
            purchase_request.save()
            msg = _(u'The following new purchase order have been created: %s.') % (', '.join(['%s' % po for po in new_pos]))
            messages.success(request, msg, fail_silently=True)

            return redirect('purchase_order_list')
    else:
        formset = ItemsFormSet(initial=initial)
    return render_to_response('generic_form.html', {
        'form':formset,
        'form_display_mode_table':True,
        'title': _(u'purchase order wizard, using purchase request source: <a href="%(url)s">%(name)s</a>') % {'url':purchase_request.get_absolute_url(), 'name':purchase_request},
        'object':purchase_request,
    }, context_instance=RequestContext(request))

def purchase_order_view(request, object_id):
    purchase_order = get_object_or_404(PurchaseOrder, pk=object_id)
    form = PurchaseOrderForm_view(instance=purchase_order)

    subtemplates = [{
            'name':'generic_list_subtemplate.html',
            'title': _(u'purchase order items'),
            'object_list':purchase_order.items.all(),
            'extra_columns':[
                {'name': _(u'qty'), 'attribute':'qty'},
                {'name': _(u'qty received'), 'attribute':'received_qty'},
                #{'name': _(u'agreed price'), 'attribute': 'fmt_agreed_price'},
                #{'name': _(u'status'), 'attribute': 'status'},
                #{'name': _(u'active'), 'attribute': 'fmt_active'}
                ],
            },]
    if request.user.is_staff:
        subtemplates.append({
                'name':'generic_list_subtemplate.html',
                'title': _(u'movements for this purchase order'),
                'object_list': purchase_order.movements.all(),
                # 'hide_links': False, # we want 'edit' there
                'extra_columns':[
                    {'name': _(u'state'), 'attribute': 'get_state_display'},
                    {'name': _(u'date'), 'attribute': 'date_act'},
                    # {'name':_(u'destination'), 'attribute': 'location_dest'}
                    ],
            },)
    return render_to_response('purchase_order_form.html', {
        'title': _(u'details for purchase order: %s') % purchase_order,
        'object':purchase_order,
        'form':form, 'form_mode': 'details',
        'subtemplates_dict': subtemplates,
    },
    context_instance=RequestContext(request))


def purchase_order_close(request, object_id):
    purchase_order = get_object_or_404(PurchaseOrder, pk=object_id)
    items = purchase_order.items.all()

    data = {
        'object':purchase_order,
        'title': _(u"Are you sure you wish to close the purchase order: %s?") % purchase_order,
    }
    if items.filter(active=True):
        data['message'] = _(u'There are still open items.')


    if purchase_order.active == False:
        msg = _(u'This purchase order has already been closed.')
        messages.error(request, msg, fail_silently=True)
        return redirect(purchase_order.get_absolute_url())


    if request.method == 'POST':
        purchase_order.active = False
        items.update(active=False)
        purchase_order.save()
        msg = _(u'The purchase order has been closed successfully.')
        messages.success(request, msg, fail_silently=True)
        return redirect(purchase_order.get_absolute_url())

    return render_to_response('generic_confirm.html', data,
    context_instance=RequestContext(request))


def purchase_order_open(request, object_id):
    purchase_order = get_object_or_404(PurchaseOrder, pk=object_id)

    data = {
        'object':purchase_order,
        'title': _(u"Are you sure you wish to open the purchase order: %s?") % purchase_order,
    }

    if purchase_order.active == True:
        msg = _(u'This purchase order is already open.')
        messages.error(request, msg, fail_silently=True)
        return redirect(request.META['HTTP_REFERER'] if 'HTTP_REFERER' in request.META else purchase_order.get_absolute_url())

    if request.method == 'POST':
        purchase_order.active = True
        purchase_order.save()
        msg = _(u'The purchase order has been opened successfully.')
        messages.success(request, msg, fail_silently=True)
        return redirect(purchase_order.get_absolute_url())

    return render_to_response('generic_confirm.html', data,
    context_instance=RequestContext(request))


def purchase_order_receive(request, object_id):
    """
    Take a purchase order and call transfer_to_inventory to transfer and
    close all of its item and close the purchase order too
    """
    purchase_order = get_object_or_404(PurchaseOrder, pk=object_id)

    msg = None
    if purchase_order.validate_user:
        msg = _(u'This purchase order has already been closed.')
    elif purchase_order.active == False:
        msg = _(u'This purchase order has already been closed.')

    if 'HTTP_REFERER' in request.META and request.path.rstrip('?') not in request.META['HTTP_REFERER']:
        # we go back to previous url, if there was one.
        url_after_this = request.META['HTTP_REFERER']
    else:
        url_after_this = purchase_order.get_absolute_url()

    if msg:
        messages.error(request, msg, fail_silently=True)
        return redirect(url_after_this)

    if request.method == 'POST':
        raise NotImplementedError
    else:
        try:
            items_left = purchase_order.calc_unmoved_items()
        except ValueError, ve:
            messages.error(request, unicode(ve), fail_silently=True)
            return redirect(url_after_this)

        form = PurchaseOrderForm_short_view(instance=purchase_order)
        dept = None
        try:
            active_role = role_from_request(request)
            if active_role:
                dept = active_role.department
        except ObjectDoesNotExist:
            pass

        if items_left and request.GET.get('do_create', False):
            if not active_role.has_perm('movements.receive_purchaseorder'):
                raise PermissionDenied
            lsrcs = Location.objects.filter(department__isnull=True, usage='procurement')[:1]
            lbdls = Location.objects.filter(department__isnull=True, usage='production')[:1]
            ldests = None
            if request.GET.get('location_ask', False):
                ldests = [Location.objects.get(pk=request.GET['location_ask']),]
            elif dept:
                ldests = Location.objects.filter(department=dept)[:1]
            if not lsrcs:
                msg = _(u'There is no procurement location configured in the system!')
                messages.error(request, msg, fail_silently=True)
            elif not ldests:
                msg = _(u'This is not default department and location for this user, please fix!')
                messages.error(request, msg, fail_silently=True)
            elif not lbdls:
                msg = _(u'This is no bundling location configured in the system!')
                messages.error(request, msg, fail_silently=True)
            else:
                movement = Movement(create_user=request.user, date_act=purchase_order.issue_date,
                        stype='in', origin=purchase_order.user_id,
                        location_src=lsrcs[0], location_dest=ldests[0],
                        purchase_order=purchase_order)
                movement.save()
                bundled = purchase_order.fill_out_movement(items_left, movement)
                if bundled:
                    # print "must put a few items in bundle, too"
                    movement = Movement(create_user=request.user, date_act=purchase_order.issue_date,
                        stype='in', origin=purchase_order.user_id,
                        location_src=lsrcs[0], location_dest=lbdls[0],
                        purchase_order=purchase_order)
                    movement.save()
                    purchase_order.fill_out_bundle_move(bundled, movement)

            # reload the request in the browser, but get rid of any "action" arguments!
            return redirect(request.path.rstrip('?'), object_id=object_id)
        elif (not items_left) and request.GET.get('do_confirm', False):
            if not (active_role and active_role.has_perm('movements.validate_purchaseorder')):
                raise PermissionDenied
            try:
                moves_pending = False
                for move in purchase_order.movements.all():
                    if move.state == 'done':
                        continue
                    if move.state != 'draft':
                        moves_pending = True
                        continue
                    if active_role.department is not None \
                            and move.location_dest.usage == 'internal' \
                            and active_role.department != move.location_dest.department:
                        # User is not allowed to validate the movement for that
                        # department, so carry on, avoid confirming the PO.
                        moves_pending = True
                        continue
                    move.do_close(val_user=request.user)
                    if move.state != 'done':
                        moves_pending = True
                if not moves_pending:
                    # First, associate bundled items to their container bundles
                    purchase_order.recalc_bundle_items()
                    for po_item in purchase_order.items.all():
                        po_item.active = False
                        po_item.status = None # TODO
                        po_item.save()
                    purchase_order.validate_user = request.user
                    purchase_order.active = False
                    purchase_order.status = None # TODO
                    purchase_order.save()
                    messages.success(request, _("Purchase order has been confirmed"), fail_silently=True)
                    return redirect(purchase_order.get_absolute_url())
                else:
                    msg = _(u'Purchase order %s cannot be confirmed, because it contains pending moves! Please inspect and close these first.') % purchase_order.user_id
                    messages.error(request, msg, fail_silently=True)
                return redirect(request.path.rstrip('?'), object_id=object_id)
            except Exception, e:
                messages.error(request, unicode(e))

        # we must ask about the remaining items or confirmation:
        form_attrs = {
            'title': _(u'details for purchase order: %s') % purchase_order,
            'more_items_count': len(items_left),
            'object':purchase_order,
            'form':form,
            'subtemplates_dict':[]
            }
        if not items_left:
            form_attrs['subtemplates_dict'].append({
                'name':'generic_list_subtemplate.html',
                'title': _(u'order items received'),
                'object_list':purchase_order.items.all(),
                'hide_links': True,
                'extra_columns':[
                    {'name': _(u'qty received'), 'attribute':'received_qty'},
                    {'name': _(u'status'), 'attribute': 'status'},
                    {'name': _(u'active'), 'attribute': 'fmt_active'}
                    ],
                })
        else:
            items_left2 = [ isinstance(k, tuple) and k[0] or k for k in items_left]
            items_in_moves = purchase_order.items.exclude(item_template__in=items_left2)
            if items_in_moves.exists():
                form_attrs['subtemplates_dict'].append({
                    'name':'generic_list_subtemplate.html',
                    'title': _(u'order items received and accounted'),
                    'object_list': items_in_moves,
                    'hide_links': True,
                    'extra_columns':[
                        {'name': _(u'qty received'), 'attribute':'received_qty'},
                        {'name': _(u'status'), 'attribute': 'status'},
                        {'name': _(u'active'), 'attribute': 'fmt_active'}
                        ],
                    })
            items_wo_moves = purchase_order.items.filter(item_template__in=items_left2)
            if items_wo_moves.exists():
                form_attrs['subtemplates_dict'].append({
                    'name':'generic_list_subtemplate.html',
                    'title': _(u'order items received but NOT accounted'),
                    'object_list': items_wo_moves,
                    'hide_links': True,
                    'extra_columns':[
                        {'name': _(u'qty pending'), 'attribute':'received_qty'},
                        {'name': _(u'status'), 'attribute': 'status'},
                        {'name': _(u'active'), 'attribute': 'fmt_active'}
                        ],
                    })
            if not dept: # rough test
                # will cause the form to ask for a location
                form_attrs['ask_location'] = True
            
        moves_list = purchase_order.movements.all()
        if moves_list:
            # add the pending movements as links
            form_attrs['subtemplates_dict'].append({
                'name':'generic_list_subtemplate.html',
                'title': _(u'movements for this purchase order'),
                'object_list': moves_list,
                # 'hide_links': False, # we want 'edit' there
                'extra_columns':[
                    {'name': _(u'state'), 'attribute': 'get_state_display'},
                    {'name': _(u'destination'), 'attribute': 'location_dest'}
                    ],
                })

        return render_to_response('po_transfer_ask.html', form_attrs, context_instance=RequestContext(request))

    raise RuntimeError


def purchase_order_item_close(request, object_id):
    purchase_order_item = get_object_or_404(PurchaseOrderItem, pk=object_id)
    data = {
        'object':purchase_order_item,
        'title': _(u'Are you sure you wish close the purchase order item: %s') % purchase_order_item,
    }

    if purchase_order_item.active == False:
        msg = _(u'This purchase order item has already been closed.')
        messages.error(request, msg, fail_silently=True)
        return redirect(request.META['HTTP_REFERER'] if 'HTTP_REFERER' in request.META else purchase_order_item.get_absolute_url())


    if request.method == 'POST':
        purchase_order_item.active = False
        purchase_order_item.save()
        msg = _(u'The purchase order item has been closed successfully.')
        messages.success(request, msg, fail_silently=True)
        return redirect(purchase_order_item.get_absolute_url())

    return render_to_response('generic_confirm.html', data,
    context_instance=RequestContext(request))


def purchase_order_item_create(request, object_id):
    purchase_order = get_object_or_404(PurchaseOrder, pk=object_id)

    if request.method == 'POST':
        form = PurchaseOrderItemForm(request.POST)#, initial={'purchase_order':purchase_order})
        if form.is_valid():
            form.save()
            msg = _(u'The purchase order item was created successfully.')
            messages.success(request, msg, fail_silently=True)
            return redirect(purchase_order.get_absolute_url())
    else:
        form = PurchaseOrderItemForm(initial={'purchase_order':purchase_order})

    return render_to_response('generic_form.html', {
        'form':form,
        'title': _(u'add new purchase order item') ,
    },
    context_instance=RequestContext(request))

class PurchaseOrderListView(GenericBloatedListView):
    queryset=PurchaseOrder.objects.by_request
    title = _(u'list of purchase orders')
    prefetch_fields = ('procurement', 'supplier')
    extra_columns = [ {'name': _('Contract'), 'attribute': 'procurement'},
                    {'name': _('Supplier'), 'attribute': 'supplier', },
                    {'name': _('Department'), 'attribute': 'department' },
                    # not needed: {'name': _('Issue date'), 'attribute': 'issue_date' },
                    {'name':_(u'Active'), 'attribute': 'fmt_active'}]

class MovementListView(GenericBloatedListView):
    queryset=Movement.objects.by_request
    title =_(u'movements')
    extra_columns=[{'name':_(u'date'), 'attribute': 'date_act'}, 
                    {'name':_(u'state'), 'attribute': 'get_state_display'},
                    {'name':_(u'type'), 'attribute': 'get_stype_display'}]

def movement_do_close(request, object_id):
    movement = get_object_or_404(Movement, pk=object_id)
    active_role = role_from_request(request)
    if request.user.is_superuser:
        pass
    elif not (active_role and active_role.has_perm('movements.validate_movement')):
        raise PermissionDenied
    try:
        if active_role.department is not None:
            if movement.stype in ('in', 'internal', 'other'):
                if active_role.department != movement.location_dest.department:
                    raise Exception(_("You do not have the permission to validate an incoming movement to %s") % movement.location_dest.department.name)
            elif movement.stype == 'out':
                if active_role.department != movement.location_src.department:
                    raise Exception(_("You do not have the permission to validate an outgoing movement from %s") % movement.location_src.department.name)
            else:
                raise Exception(_("Unexpected movement type, you do not have permission to validate"))

        movement.do_close(request.user)
        cart_utils.remove_from_session(request, movement)
        messages.success(request, _(u'The movement has been validated.'))
    except Exception, e:
        messages.error(request, unicode(e))

    return redirect(movement.get_absolute_url())

def repair_itemgroup(request, object_id):
    item = get_object_or_404(ItemGroup, pk=object_id)
    active_role = role_from_request(request)
    if not active_role.has_perm('assets.change_itemgroup'):
        raise PermissionDenied

    data = {'title': _("Repair of asset"), }
    # we need data for the three columns:
    # TODO: load pending movements and pre-populate our data

    # A: the locations we can fetch from + their available parts
    if active_role:
        dept = active_role.department
        if not (request.user.is_staff or (dept and dept == item.location.department)):
            raise PermissionDenied
    else:
        dept = item.location.department
    
    may_contain = [ mc.category for mc in item.item_template.category.may_contain.all()]
    print "May contain:", may_contain
    
    data['src_locations'] = []
    for loc in Location.objects.filter(department=dept):
        data['src_locations'].append((loc, Item.objects.filter(location=loc, \
                                        item_template__category__in=may_contain)))
    
    # B: the current details of the item
    data['item'] = item
    
    # C: the locations we can send parts to:
    data['dest_locations'] = list(Location.objects.filter(department=dept, usage='internal'))
    data['dest_locations'] += list(Location.objects.filter(department__isnull=True, 
                name__in=[ unicode(_(u'Destroy')), unicode(_(u'Lost'))]))
    
    return render_to_response('repair_item.html', data, context_instance=RequestContext(request))

class RepairOrderListView(GenericBloatedListView):
    queryset=RepairOrder.objects.by_request
    title = _(u'list of repair orders')
    # prefetch_fields = ('procurement', 'supplier')
    extra_columns = [ {'name': _('Department'), 'attribute': 'department' },
                    {'name':_(u'Active'), 'attribute': 'fmt_active'},
                    ]

class POCartOpenView(CartOpenView):
    model=PurchaseOrder
    exclusive = True

class POItemCartOpenView(CartOpenView):
    model=PurchaseOrderItem
    exclusive = True

class POIAddMainView(_ModifyCartView):
    cart_model=PurchaseOrderItem

    def _add_or_remove(self, cart, obj):
        verb = cart.set_main_product(obj)
        message = _("%(item)s set in %(description)s") % {'item': unicode(obj), 'description': unicode(cart.item_name)}
        return message, verb

    def get_redirect_url(self, **kwargs):
        # always return to the PO view, no need to select a second product
        return self.cart_object.get_cart_url()

class POIAddBundledView(_ModifyCartView):
    cart_model=PurchaseOrderItem

    def _add_or_remove(self, cart, obj):
        verb = cart.add_to_cart(obj)
        if cart.item_template:
            main = unicode(cart.item_template)
        else:
            main = cart.item_name
        message = _("%(item)s added to bundle for %(main)s") % {'item': unicode(obj), 'main': main}
        return message, verb
#eof