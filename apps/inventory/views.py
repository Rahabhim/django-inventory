# -*- encoding: utf-8 -*-

from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from django.views.generic.list_detail import object_list
# from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError

from common.models import Supplier
from common.api import role_from_request

from models import Inventory, \
                   InventoryItem

#from inventory import location_filter

from forms import InventoryForm_view, InventoryItemForm


def inventory_view(request, object_id):
    inventory = get_object_or_404(Inventory, pk=object_id)
    form = InventoryForm_view(instance=inventory)

    asset_qty={}
    for t in inventory.items.all():
        if t.asset in asset_qty:
            asset_qty[t.asset] = asset_qty[t.asset] + t.quantity
        else:
            asset_qty[t.asset] = t.quantity

    supplies_list = [{'item_template':x, 'qty':y} for x,y in asset_qty.items()]

    return render_to_response('generic_detail.html', {
        'object_name':_(u'inventory'),
        'object':inventory,
        'form':form,
        'subtemplates_dict':[
            {
                'name':'generic_list_subtemplate.html',
                'title':_(u'current balances for inventory'),
                'object_list':supplies_list,
                'main_object':'item_template',
                'extra_columns':[{'name':_(u'quantity'),'attribute':'qty'}],

            }
        ]
    },
    context_instance=RequestContext(request))


def supplier_purchase_orders(request, object_id):
    supplier = get_object_or_404(Supplier, pk=object_id)
    return object_list(
        request,
        queryset = supplier.purchaseorder_set.all(),
        template_name = "generic_list.html",
        extra_context=dict(
            title = '%s: %s' % (_(u"purchase orders from supplier"), supplier),
        ),
    )

def inventory_items_compare(request, object_id):
    inventory = get_object_or_404(Inventory, pk=object_id)
    form = InventoryForm_view(instance=inventory)
    subtemplates_dict = []
    
    if request.method == 'POST':
        raise NotImplementedError
    else:
        offset = request.GET.get('offset', 0)
        limit = request.GET.get('limit', 10)
        pending_only = request.GET.get('pending_only', False)

        have_pending, res = inventory._compute_state(pending_only=pending_only, offset=offset, limit=limit)

        if res:
            subtemplates_dict.append({ 'name':'inventory_items_compare.html',
                            'object_list': res, })

        if have_pending:
            subtemplates_dict.append({'name': 'inventory_compare_have_more.html'})
        else:
            subtemplates_dict.append({'name': 'inventory_compare_success.html'})

    return render_to_response('inventory_compare_details.html', {
            'object_name':_(u'inventory'),
            'object':inventory,
            'form':form, 'form_mode': 'details',
            'subtemplates_dict': subtemplates_dict,
            },
        context_instance=RequestContext(request))

def inventory_validate(request, object_id):
    # file upload?
    inventory = get_object_or_404(Inventory, pk=object_id)
    try:
        active_role = role_from_request(request)
        if not (active_role and active_role.has_perm('inventory.validate_inventory')):
            raise PermissionDenied
        # check that active_role has the same dept as inventory!
        if active_role.department != inventory.location.department:
            raise PermissionDenied(_("You are not currently signed at the same Department as this Inventory"))

        # actual act of closing the inventory: (note, we don't pass the date)
        inventory.do_close(request.user)
        messages.success(request, _("The inventory has been validated and all movements fixated"), fail_silently=True)
    except ValidationError, e:
        for msg in e.messages:
            messages.error(request, msg, fail_silently=True)
    except PermissionDenied, e:
        messages.error(request, _("Permission denied: %s") % e, fail_silently=True)
    except ObjectDoesNotExist, e:
        messages.error(request, _("Incorrect role or department to validate inventory: %s") % e, fail_silently=True)
    return redirect('inventory_view', object_id=object_id)

#eof