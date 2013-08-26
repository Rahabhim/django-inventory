# -*- encoding: utf-8 -*-
import datetime
import logging
from collections import defaultdict

from django import forms
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect #, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404, redirect, render
from django.template import RequestContext
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
#from django.contrib.contenttypes.models import ContentType
#from django.views.generic.list_detail import object_detail, object_list
#from django.core.urlresolvers import reverse
#from django.views.generic.create_update import create_object
from django.forms.formsets import formset_factory

from common.models import Supplier, Location, LocationTemplate
from common.api import role_from_request
from assets.models import ItemTemplate, Item, ItemGroup
from generic_views.views import GenericBloatedListView, CartOpenView, _ModifyCartView
from main import cart_utils

from company.models import Department
from models import PurchaseRequest, PurchaseOrder, \
                    Movement, RepairOrder
from forms import PurchaseRequestForm_view, PurchaseRequestItemForm, \
                  PurchaseOrderForm_view, PurchaseOrderItemForm, \
                  PurchaseOrderItem, PurchaseOrderWizardItemForm, \
                  PurchaseOrderForm_short_view

from weird_fields import DeptSelectMultipleField

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
            'hide_link': True,
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
        'title': _(u'details for purchase order'),
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


    if purchase_order.state in ('done', 'reject'):
        msg = _(u'This purchase order has already been closed.')
        messages.error(request, msg, fail_silently=True)
        return redirect(purchase_order.get_absolute_url())


    if request.method == 'POST':
        purchase_order.state = 'done'
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

    if purchase_order.state in ('draft',):
        msg = _(u'This purchase order is already open.')
        messages.error(request, msg, fail_silently=True)
        return redirect(request.META['HTTP_REFERER'] if 'HTTP_REFERER' in request.META else purchase_order.get_absolute_url())

    if request.method == 'POST':
        purchase_order.state = 'draft'
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
    elif purchase_order.state not in ('draft', 'pending'):
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
            mapped_items = purchase_order.map_items()
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

        items_left = purchase_order.map_has_left(mapped_items)
        if items_left and request.GET.get('do_create', False):
            if not active_role.has_perm('movements.receive_purchaseorder'):
                raise PermissionDenied
            if request.GET.get('location_ask', False):
                master_loc = Location.objects.get(pk=request.GET['location_ask'])
            elif dept:
                master_loc = Location.objects.filter(department=dept)[:1][0]
            else:
                messages.error(request,_('You must select a location!'), fail_silently=True)
                return redirect(request.path.rstrip('?'), object_id=object_id)

            purchase_order.items_into_moves(mapped_items, request, dept, master_loc)

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
                    for po_item in purchase_order.items.all():
                        po_item.active = False
                        po_item.status = None # TODO
                        po_item.save()
                    purchase_order.validate_user = request.user
                    purchase_order.state = 'done'
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
            'more_items_count': items_left,
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

def purchase_order_reject(request, object_id):
    """ Reject the purchase order

    """
    purchase_order = get_object_or_404(PurchaseOrder, pk=object_id)

    msg = None
    if purchase_order.validate_user:
        msg = _(u'This purchase order has already been closed.')
    elif purchase_order.state not in ('draft', 'pending'):
        msg = _(u'This purchase order has already been closed.')

    if 'HTTP_REFERER' in request.META and request.path.rstrip('?') not in request.META['HTTP_REFERER']:
        # we go back to previous url, if there was one.
        url_after_this = request.META['HTTP_REFERER']
    else:
        url_after_this = purchase_order.get_absolute_url()

    if msg:
        messages.error(request, msg, fail_silently=True)
        return redirect(url_after_this)

    if request.user.is_staff:
        pass
    else:
        try:
            active_role = role_from_request(request)
            if not (active_role and active_role.has_perm('movements.validate_purchaseorder') \
                    and active_role.department):
                raise PermissionDenied
            if active_role.department != purchase_order.department:
                raise PermissionDenied
        except ObjectDoesNotExist:
            raise PermissionDenied
    
    if request.method == 'POST' and request.REQUEST.get('confirm', False) == '1':
        try:
            purchase_order.do_reject(request.user)
            messages.success(request, _("The purchase order has been marked as rejected"), fail_silently=True)
        except Exception, e:
            messages.error(request, e, fail_silently=True)
        return redirect(url_after_this)
    else:
        return render_to_response('po_reject_ask.html', dict(object=purchase_order), context_instance=RequestContext(request))

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

class POCopyForm(forms.Form):
    purchase_order = forms.ModelChoiceField(queryset=PurchaseOrder.objects.all(), widget=forms.widgets.HiddenInput, required=True)
    # loc_template = forms.ModelChoiceField(queryset=LocationTemplate.objects.filter(sequence__lt=100), widget=forms.widgets.RadioSelect, required=True)
    issue_date = forms.DateField(label=_("Date"), required=True, initial=datetime.date.today,
                    help_text=_("Format: 23/04/2010"))
    depts = DeptSelectMultipleField('departments_list', label=_("Departments"), show_help_text=False)

def purchase_order_copy(request, object_id):
    po_instance = get_object_or_404(PurchaseOrder.objects.by_request(request), pk=object_id)
    logger = logging.getLogger('apps.movements.po_copy')

    if request.method == 'POST' and 'submit' in request.POST:
        form = POCopyForm(request.POST)
        if form.is_valid():
            new_date = form.cleaned_data['issue_date']

            # Step 1: check that user can create POs for every department requested
            logger.debug("Step 1")
            depts = set(form.cleaned_data['depts'])
            departments = []

            for role in request.user.dept_roles.all():
                if role.department.id not in depts:
                    continue
                if not role.has_perm('movements.create_purchaseorder'):
                    logger.warning("User %s not allowed to create PO for dept %s", request.user, role.department)
                    raise PermissionDenied
                depts.remove(role.department.id)
                departments.append(role.department)

            if len(depts):
                if request.user.is_staff or request.user.is_superuser:
                    for dept in Department.objects.filter(id__in=depts):
                        departments.append(dept)
                else:
                    logger.warning("User %s has no role for departments %r", request.user, list(depts))
                    raise PermissionDenied

            # Step 2: Code that copies a PO + its items:
            logger.debug("Step 2")
            all_new_pos = []
            counter = 1
            for dept in departments:
                new_user_id = None # '%s/%d' %(po_instance.user_id or '', counter)
                counter += 1
                new_po = PurchaseOrder(user_id=new_user_id,
                            purchase_request=po_instance.purchase_request,
                            procurement=po_instance.procurement, create_user=request.user,
                            supplier=po_instance.supplier, issue_date=new_date,
                            notes=po_instance.notes, department=dept)
                new_po.save()
                line_map = {}
                in_group_defer = []
                for item in po_instance.items.all():
                    npi = new_po.items.create(item_name=item.item_name,
                            item_template=item.item_template, agreed_price=item.agreed_price,
                            qty=item.qty, received_qty=item.received_qty)
                    line_map[item.id] = npi.id
                    if item.in_group:
                        in_group_defer.append((npi.id, item.in_group))

                    for bit in item.bundled_items.all():
                        npi.bundled_items.create(item_template=bit.item_template, qty=bit.qty)

                if in_group_defer:
                    for pk, grp_line in in_group_defer:
                        contained = new_po.items.get(pk=pk)
                        group_pk = line_map.get(grp_line, None)
                        if not group_pk:
                            logger.warning("Algo failure: cannot locate group %s", grp_line)
                            continue
                        contained.in_group = group_pk
                        contained.save()

                all_new_pos.append(new_po)
            # end of loop, we have saved some POs, so far

            # shortcut, stop here:
            logger.debug("Finish")
            return redirect('purchase_order_pending_list')
        if False:
            # DISABLED CODE: remove 4 lines above to enable automatic moves!
            # Step 3: sort items for each PO and create the moves
            logger.debug("Step 3")
            loc_template = form.cleaned_data['loc_template']
            for new_po in all_new_pos:
                try:
                    mapped_items = new_po.map_items()
                except ValueError, ve:
                    messages.error(request, unicode(ve), fail_silently=True)
                    continue
                try:
                    if new_po.map_has_left(mapped_items):
                        if mapped_items.get('', None):
                            # we have items that could go to any location, "move" them to
                            # our location /kind/
                            it_tmpls = mapped_items.pop('')
                            loc_its = mapped_items[loc_template.id]
                            for tmpl_id, objs in it_tmpls.items():
                                loc_its.setdefault(tmpl_id, []).extend(objs)
                        new_po.items_into_moves(mapped_items, request, new_po.department, False)
                except Exception, e:
                    messages.error(request, unicode(e), fail_silently=True)
                    continue

            logger.debug("Finish")
            return redirect('purchase_order_pending_list')
        # else: form is invalid, stay there.
    else:
        old_dept = None
        # check if the PO can be copied
        for move in po_instance.movements.all():
            if move.location_dest.department:
                if old_dept and move.location_dest.department != old_dept:
                    messages.error(request, _('This Purchase Order used more than one Department, cannot copy.'), fail_silently=True)
                    return redirect(po_instance.get_absolute_url())
                elif not old_dept:
                    old_dept = move.location_dest.department
        # Just a blank copy form:
        form = POCopyForm(initial={'purchase_order': po_instance, 'date_mode': 'original' })

    po_form = PurchaseOrderForm_view(instance=po_instance)

    subtemplates = [{
            'name':'generic_list_subtemplate.html',
            'title': _(u'purchase order items'),
            'object_list':po_instance.items.all(),
            'hide_link': True,
            'extra_columns':[
                {'name': _(u'qty'), 'attribute':'qty'},
                {'name': _(u'qty received'), 'attribute':'received_qty'},
                ],
            },]

    return render(request, 'po_copy_view.html', { 'title': _("Purchase Order Copy"),
                'form': form, 'form_mode': 'create',
                'po_form': po_form, 'subtemplates': subtemplates,
                'object': po_instance })


class PurchaseOrderListView(GenericBloatedListView):
    queryset=PurchaseOrder.objects.by_request
    title = _(u'list of purchase orders')
    prefetch_fields = ('procurement', 'supplier')
    extra_columns = [ {'name': _('Contract'), 'attribute': 'procurement'},
                    {'name': _('Supplier'), 'attribute': 'supplier', },
                    {'name': _('Department'), 'attribute': 'department' },
                    # not needed: {'name': _('Issue date'), 'attribute': 'issue_date' },
                    {'name':_(u'state'), 'attribute': 'get_state_display', 'order_attribute': 'state'}]

class MovementListView(GenericBloatedListView):
    queryset=Movement.objects.by_request
    title =_(u'movements')
    order_by = '-date_act'
    extra_columns=[{'name':_(u'date'), 'attribute': 'date_act'}, 
                    {'name':_(u'state'), 'attribute': 'get_state_display', 'order_attribute': 'state'},
                    {'name':_(u'type'), 'attribute': 'get_stype_display', 'order_attribute': 'stype'}]

def movement_do_close(request, object_id):
    movement = get_object_or_404(Movement, pk=object_id)
    active_role = role_from_request(request)
    if request.user.is_superuser:
        pass
    elif not (active_role and active_role.has_perm('movements.validate_movement')):
        raise PermissionDenied
    try:
        if active_role.department is not None:
            if movement.stype in ('in', 'other'):
                if active_role.department != movement.location_dest.department:
                    raise Exception(_("You do not have the permission to validate an incoming movement to %s") % movement.location_dest.department.name)
                movement.do_close(movement.validate_user)
                messages.success(request, _(u'The movement has been validated.'))
            elif movement.stype == 'internal':
                # Internal moves may need validation from both source and destination
                # departments, if those are different

                if active_role.department == movement.location_dest.department:
                    # We are called by a user on the receiving end
                    if movement.location_src.department == movement.location_dest.department \
                            or movement.src_validate_user \
                            or movement.location_src.department is None \
                            or movement.location_src.department.deprecate \
                            or movement.location_src.department.merge:
                            # In these cases, we don't need the sending end, we can proceed
                        movement.do_close(request.user)
                        messages.success(request, _(u'The movement has been validated.'))
                    else:
                        # here, we need to defer validation until the sending end approves, too
                        # we only set the 'validate_user', but not 'date_val', so that
                        # the sending end can validate in one go.
                        movement._close_check()
                        movement.validate_user = request.user
                        movement.save()
                        messages.warning(request, _('Movement has been validated by you, but is still pending validation from source department'))

                elif active_role.department == movement.location_src.department:
                    # That's the sending side. Mark our approval, and then perhaps close
                    # the movement, if receiving side has agreed.
                    movement._close_check()
                    movement.src_validate_user = request.user
                    movement.src_date_val = datetime.date.today()
                    movement.save()
                    if movement.validate_user:
                        movement.do_close(movement.validate_user)
                        messages.success(request, _(u'The movement has been validated.'))
                    else:
                        messages.warning(request, _(u'You have approved the move, and now it is pending validation from the destination department.'))

                else:
                    raise Exception(_("You do not have the permission to validate an incoming movement to %s") %\
                                    movement.location_dest.department.name)

            elif movement.stype == 'out':
                if active_role.department != movement.location_src.department:
                    raise Exception(_("You do not have the permission to validate an outgoing movement from %s") % movement.location_src.department.name)
                movement.do_close(movement.validate_user)
                messages.success(request, _(u'The movement has been validated.'))
            else:
                raise Exception(_("Unexpected movement type, you do not have permission to validate"))

        else:
            movement.do_close(movement.validate_user)
            messages.success(request, _(u'The movement has been validated.'))

        cart_utils.remove_from_session(request, movement)
    except Exception, e:
        messages.error(request, unicode(e))

    return redirect(movement.get_absolute_url())

def movement_do_reject(request, object_id):
    movement = get_object_or_404(Movement, pk=object_id)
    active_role = role_from_request(request)
    if request.user.is_superuser:
        pass
    elif not (active_role and active_role.has_perm('movements.validate_movement')):
        raise PermissionDenied
    try:
        if active_role.department is not None:
            if movement.stype in ('in', 'other'):
                if active_role.department != movement.location_dest.department:
                    raise Exception(_("You do not have the permission to reject an incoming movement to %s") % movement.location_dest.department.name)
                movement.do_reject(movement.validate_user)
                messages.success(request, _(u'The movement has been rejected.'))
            elif movement.stype == 'internal':
                # Internal moves may need validation from both source and destination
                # departments, if those are different

                if active_role.department == movement.location_src.department \
                        or active_role.department == movement.location_dest.department:
                    # Either end can reject a movement to/from their dept
                    movement.do_reject(request.user)
                    messages.success(request, _(u'The movement has been rejected.'))
                else:
                    raise Exception(_("You do not have the permission to reject an incoming movement to %s") %\
                                    movement.location_dest.department.name)

            elif movement.stype == 'out':
                if active_role.department != movement.location_src.department:
                    raise Exception(_("You do not have the permission to reject an outgoing movement from %s") % movement.location_src.department.name)
                movement.do_reject(movement.validate_user)
                messages.success(request, _(u'The movement has been rejected.'))
            else:
                raise Exception(_("Unexpected movement type, you do not have permission to reject"))

        else:
            movement.do_reject(movement.validate_user)
            messages.success(request, _(u'The movement has been rejected.'))

        cart_utils.remove_from_session(request, movement)
    except Exception, e:
        messages.error(request, unicode(e))

    return redirect(movement.get_absolute_url())

def repair_itemgroup(request, object_id):
    item = get_object_or_404(ItemGroup, pk=object_id)
    active_role = role_from_request(request)
    logger = logging.getLogger('apps.movements.repair')
    if not (request.user.is_superuser or active_role.has_perm('assets.change_itemgroup')):
        logger.warning("User %s is not allowed to repair item", request.user)
        raise PermissionDenied

    data = {'title': _("Repair of asset"), }
    # we need data for the three columns:
    # TODO: load pending movements and pre-populate our data

    item_location = item.location
    if not item_location:
        logger.warning("Item %d %s does not belong to any location, cannot repair", item.id, item)
        raise PermissionDenied
    elif not item_location.department:
        # search for a bundle in bundle
        parents = item.bundled_in.all()
        if parents and len(parents) > 1:
            messages.error(request, _('Internal error: item is contained in %d bundles!') % len(parents))
            return HttpResponseRedirect(item.get_absolute_url())
        elif parents and parents[0].location and parents[0].location.department:
            item_location = parents[0].location
        else:
            logger.warning("Item %d %s, nor its parent belong to any location", item.id, item)
            raise PermissionDenied

    # A: the locations we can fetch from + their available parts
    if active_role:
        dept = active_role.department
        if request.user.is_staff:
            pass
        elif item_location and dept and dept == item_location.department:
            pass
        else:
            logger.warning("User %s does not have active_role for dept %s to edit item %d %s",
                        request.user, item_location.department, item.id, item)
            raise PermissionDenied
    else:
        dept = item_location.department
    
    if dept is None:
        # cannot edit bundles not in a department. Reason is, the rest of this algo
        # will completely bork
        logger.warning("Department for item %d %s is not specified, cannot allow repair",
                    item.id, item)
        raise PermissionDenied

    if request.method == 'POST':
        try:
            df = forms.DateField()
            issue_date = df.to_python(request.REQUEST['issue_date'])
            user_id = request.REQUEST['user_id']

            if not issue_date:
                raise ValueError(_("Issue date cannot be empty"))

            bundle_location = Location.objects.filter(department__isnull=True, usage='production')[:1][0]

            # TODO: amend an existing order
            reform = RepairOrder(item=item, create_user=request.user, user_id=user_id,
                        issue_date=issue_date, department=dept, notes=request.REQUEST['notes'])

            reform.save()
            # parts_in
            if 'parts_in' in request.POST:
                for item in Item.objects.filter(id__in=map(long, request.POST.getlist('parts_in'))):
                    move, c = Movement.objects.get_or_create(repair_order=reform,
                                location_src=item.location, location_dest=bundle_location,
                                defaults={'create_user': request.user,
                                        'date_act': issue_date, 'name': user_id,
                                        'stype': 'in'})
                    move.items.add(item)

            if 'parts_out' in request.POST:
                # First, group the items per destination location
                # They have come like ['loc:item-id', ...] in the POST request
                parts_out = defaultdict(list)
                for pp in request.POST.getlist('parts_out'):
                    loc, iid = map(long, pp.split(':', 1))
                    parts_out[loc].append(iid)

                for loc_id, iids in parts_out.items():
                    move, c = Movement.objects.get_or_create(repair_order=reform,
                                location_src=bundle_location, location_dest_id=loc_id,
                                defaults={'create_user': request.user,
                                        'date_act': issue_date, 'name': user_id,
                                        'stype': 'in'})
                    for item in Item.objects.filter(id__in=iids):
                        move.items.add(item)
            # Repair Order and its moves are created, get out of here!
            return redirect(reform.get_absolute_url())
        except Exception:
            logger.warning("Exception at repair:", exc_info=True)
            # continue with our form, ask again.

    may_contain = [ mc.category for mc in item.item_template.category.may_contain.all()]

    data['src_locations'] = []
    for loc in Location.objects.filter(department=dept):
        data['src_locations'].append((loc, Item.objects.filter(location=loc, \
                                        item_template__category__in=may_contain) \
                                        .order_by('item_template__category', 'item_template')))

    # B: the current details of the item
    data['item'] = item

    # C: the locations we can send parts to:
    data['dest_locations'] = list(Location.objects.filter(department=dept, usage='internal'))
    data['dest_locations'] += list(Location.objects.filter(department__isnull=True,
                name__in=[ unicode(_(u'Destroy')), unicode(_(u'Lost'))]))

    return render_to_response('repair_item.html', data, context_instance=RequestContext(request))

def repair_do_close(request, object_id):
    """ Close moves of repair order; then the order itself
    """
    repair = get_object_or_404(RepairOrder, pk=object_id)
    active_role = role_from_request(request)
    if request.user.is_superuser:
        pass
    elif not (active_role and active_role.has_perm('movements.validate_repairorder')):
        raise PermissionDenied
    try:
        if (active_role.department is not None) \
                and active_role.department != repair.department:
            raise Exception(_("You do not have the permission to validate a repair order for %s") % repair.department.name)

        moves_pending = False

        for move in repair.movements.all():
            if move.state == 'done':
                continue
            if move.state != 'draft':
                moves_pending = True
                continue
            if active_role.department is not None \
                    and move.location_dest.usage == 'internal' \
                    and active_role.department != move.location_dest.department:
                moves_pending = True
                continue
            elif active_role.department is not None \
                    and move.location_src.usage == 'internal' \
                    and active_role.department != move.location_src.department:
                moves_pending = True
                continue
            move.do_close(val_user=request.user)
            if move.state != 'done':
                moves_pending = True
        if not moves_pending:
            repair.do_close(request.user)
            messages.success(request, _("Repair order has been confirmed"), fail_silently=True)
            return redirect(repair.get_absolute_url())
        else:
            msg = _(u'Repair order %s cannot be confirmed, because it contains pending moves! Please inspect and close these first.') % repair.user_id
            messages.error(request, msg, fail_silently=True)
    except Exception, e:
        messages.error(request, unicode(e))


    return redirect(repair.get_absolute_url())


class RepairOrderListView(GenericBloatedListView):
    queryset=RepairOrder.objects.by_request
    title = _(u'list of repair orders')
    # prefetch_fields = ('procurement', 'supplier')
    extra_columns = [ {'name': _('Department'), 'attribute': 'department' },
                    {'name':_(u'State'), 'attribute': 'get_state_display', 'order_attribute': 'state'},
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