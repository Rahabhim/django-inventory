# -*- encoding: utf-8 -*-
import datetime

from django.utils.translation import ugettext as _
#from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.contrib import messages
#from django.contrib.contenttypes.models import ContentType
#from django.views.generic.list_detail import object_detail, object_list
#from django.core.urlresolvers import reverse
#from django.views.generic.create_update import create_object
from django.forms.formsets import formset_factory

from common.models import Supplier, Location
from assets.models import ItemTemplate
from generic_views.views import GenericBloatedListView
from main import cart_utils

from models import PurchaseRequest, PurchaseRequestItem, PurchaseOrder, Movement
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
        'title':_(u'add new purchase request item') ,
    },
    context_instance=RequestContext(request))


def purchase_request_close(request, object_id):
    purchase_request = get_object_or_404(PurchaseRequest, pk=object_id)

    data = {
        'object':purchase_request,
        'title':_(u"Are you sure you wish to close the purchase request: %s?") % purchase_request,
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
        'title':_(u'purchase order wizard, using purchase request source: <a href="%(url)s">%(name)s</a>') % {'url':purchase_request.get_absolute_url(), 'name':purchase_request},
        'object':purchase_request,
    }, context_instance=RequestContext(request))

def purchase_order_view(request, object_id):
    purchase_order = get_object_or_404(PurchaseOrder, pk=object_id)
    form = PurchaseOrderForm_view(instance=purchase_order)

    subtemplates = [{
            'name':'generic_list_subtemplate.html',
            'title':_(u'purchase order items'),
            'object_list':purchase_order.items.all(),
            'extra_columns':[
                {'name':_(u'qty'), 'attribute':'qty'},
                {'name':_(u'qty received'), 'attribute':'received_qty'},
                {'name':_(u'agreed price'), 'attribute': 'fmt_agreed_price'},
                {'name':_(u'status'), 'attribute': 'status'},
                {'name':_(u'active'), 'attribute': 'fmt_active'}
                ],
            },
            {
                'name':'generic_list_subtemplate.html',
                'title':_(u'movements for this purchase order'),
                'object_list': purchase_order.movements.all(),
                # 'hide_links': False, # we want 'edit' there
                'extra_columns':[
                    {'name':_(u'state'), 'attribute': 'state'},
                    {'name':_(u'date'), 'attribute': 'date_act'},
                    # {'name':_(u'destination'), 'attribute': 'location_dest'}
                    ],
            },
        ]
    return render_to_response('generic_detail.html', {
        'title':_(u'details for purchase order: %s') % purchase_order,
        'object':purchase_order,
        'form':form,
        'subtemplates_dict': subtemplates,
    },
    context_instance=RequestContext(request))


def purchase_order_close(request, object_id):
    purchase_order = get_object_or_404(PurchaseOrder, pk=object_id)
    items = purchase_order.items.all()

    data = {
        'object':purchase_order,
        'title':_(u"Are you sure you wish to close the purchase order: %s?") % purchase_order,
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
        'title':_(u"Are you sure you wish to open the purchase order: %s?") % purchase_order,
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

    if msg:
        messages.error(request, msg, fail_silently=True)
        return redirect(request.META['HTTP_REFERER'] if 'HTTP_REFERER' in request.META else purchase_order.get_absolute_url())


    if request.method == 'POST':
        raise NotImplementedError
    else:
        items_left = purchase_order.calc_unmoved_items()

        form = PurchaseOrderForm_short_view(instance=purchase_order)
        
        if items_left and request.GET.get('do_create', False):
            lsrcs = Location.objects.filter(department__isnull=True, usage='procurement')[:1]
            dept = request.user.get_profile().department
            if dept:
                ldests = Location.objects.filter(department=dept)[:1]
            if not lsrcs:
                msg = _(u'There is no procurement location configured in the system!')
                messages.error(request, msg, fail_silently=True)
            elif not ldests:
                msg = _(u'This is not default department and location for this user, please fix!')
                messages.error(request, msg, fail_silently=True)
            else:
                movement = Movement(create_user=request.user, date_act=datetime.date.today(),
                        stype='in', origin=purchase_order.user_id,
                        location_src=lsrcs[0], location_dest=ldests[0],
                        purchase_order=purchase_order)
                movement.save()
                purchase_order.fill_out_movement(items_left, movement)
            pass
        elif (not items_left) and request.GET.get('confirm', False):
            raise NotImplementedError

        # we must ask about the remaining items or confirmation:
        form_attrs = {
            'title':_(u'details for purchase order: %s') % purchase_order,
            'more_items_count': len(items_left),
            'object':purchase_order,
            'form':form,
            'subtemplates_dict':[]
            }
        if not items_left:
            form_attrs['subtemplates_dict'].append({
                'name':'generic_list_subtemplate.html',
                'title':_(u'order items received'),
                'object_list':purchase_order.items.all(),
                'hide_links': True,
                'extra_columns':[
                    {'name':_(u'qty received'), 'attribute':'received_qty'},
                    {'name':_(u'status'), 'attribute': 'status'},
                    {'name':_(u'active'), 'attribute': 'fmt_active'}
                    ],
                })
        else:
            items_in_moves = purchase_order.items.exclude(item_template__in=items_left.keys())
            if items_in_moves.exists():
                form_attrs['subtemplates_dict'].append({
                    'name':'generic_list_subtemplate.html',
                    'title':_(u'order items received and accounted'),
                    'object_list': items_in_moves,
                    'hide_links': True,
                    'extra_columns':[
                        {'name':_(u'qty received'), 'attribute':'received_qty'},
                        {'name':_(u'status'), 'attribute': 'status'},
                        {'name':_(u'active'), 'attribute': 'fmt_active'}
                        ],
                    })
            items_wo_moves = purchase_order.items.filter(item_template__in=items_left.keys())
            if items_wo_moves.exists():
                form_attrs['subtemplates_dict'].append({
                    'name':'generic_list_subtemplate.html',
                    'title':_(u'order items received but NOT accounted'),
                    'object_list': items_wo_moves,
                    'hide_links': True,
                    'extra_columns':[
                        {'name':_(u'qty pending'), 'attribute':'received_qty'},
                        {'name':_(u'status'), 'attribute': 'status'},
                        {'name':_(u'active'), 'attribute': 'fmt_active'}
                        ],
                    })
            
        moves_list = purchase_order.movements.all()
        if moves_list:
            # add the pending movements as links
            form_attrs['subtemplates_dict'].append({
                'name':'generic_list_subtemplate.html',
                'title':_(u'movements for this purchase order'),
                'object_list': moves_list,
                # 'hide_links': False, # we want 'edit' there
                'extra_columns':[
                    {'name':_(u'state'), 'attribute': 'state'},
                    {'name':_(u'destination'), 'attribute': 'location_dest'}
                    ],
                })

        return render_to_response('po_transfer_ask.html', form_attrs, context_instance=RequestContext(request))

    raise RuntimeError
    return {}


def purchase_order_item_close(request, object_id):
    purchase_order_item = get_object_or_404(PurchaseOrderItem, pk=object_id)
    data = {
        'object':purchase_order_item,
        'title':_(u'Are you sure you wish close the purchase order item: %s') % purchase_order_item,
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
        'title':_(u'add new purchase order item') ,
    },
    context_instance=RequestContext(request))

class PurchaseOrderListView(GenericBloatedListView):
    queryset=PurchaseOrder.objects.all()
    title =_(u'purchase orders')
    extra_columns = [{'name':_(u'Active'), 'attribute': 'fmt_active'}]

class MovementListView(GenericBloatedListView):
    queryset=Movement.objects.all()
    title =_(u'movements')
    extra_columns=[{'name':_(u'date'), 'attribute': 'date_act'}, 
                    {'name':_(u'state'), 'attribute': 'get_state_display'},
                    {'name':_(u'type'), 'attribute': 'get_stype_display'}]

def movement_do_close(request, object_id):
    movement = get_object_or_404(Movement, pk=object_id)
    try:
        movement.do_close(request.user)
        cart_utils.remove_from_session(request, movement)
        messages.success(request, _(u'The movement has been validated.'))
    except Exception, e:
        messages.error(request, unicode(e))

    return redirect(movement.get_absolute_url())

def repair_itemgroup(request):
    raise NotImplementedError

#eof