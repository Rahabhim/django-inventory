# -*- encoding: utf-8 -*-
import logging
import datetime
import subprocess
from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from django.http import HttpResponse
from django.views.generic.list_detail import object_list
# from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError

from common.models import Supplier
from common.api import role_from_request

from models import Inventory

from forms import InventoryForm_view, InventoryValidateForm
from conf import settings as app_settings

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
        'title':_(u'Inventory details'),
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
            'have_pending': bool(have_pending),
            'object_name':_(u'inventory'),
            'object':inventory,
            'form':form, 'form_mode': 'details',
            'subtemplates_dict': subtemplates_dict,
            },
        context_instance=RequestContext(request))

def inventory_validate(request, object_id):
    # file upload?
    inventory = get_object_or_404(Inventory, pk=object_id)
    form = InventoryValidateForm(request.POST, request.FILES, instance=inventory)
    try:
        active_role = role_from_request(request)
        if request.user.is_superuser and settings.DEVELOPMENT:
            pass
        elif not (active_role and active_role.has_perm('inventory.validate_inventory')):
            raise PermissionDenied(_("Your active role does not have permission to validate an inventory"))
        # check that active_role has the same dept as inventory!
        elif active_role.department != inventory.location.department:
            raise PermissionDenied(_("You are not currently signed at the same Department as this Inventory"))

        # actual act of closing the inventory: (note, we don't pass the date)
        if request.method == 'POST' and form.is_valid() and inventory.signed_file and inventory.name:
            inventory.save() # for the file
            if getattr(app_settings, 'signature_verify_bin', False):
                try:
                    subprocess.check_call([app_settings.signature_verify_bin, inventory.signed_file.path])
                except subprocess.CalledProcessError:
                    inventory.signed_file.delete(save=True)
                    raise
            inventory.do_close(request.user)
            messages.success(request, _("The inventory has been validated and all movements fixated"), fail_silently=True)

            return redirect('inventory_view', object_id=object_id)
        elif request.method == 'POST':
            messages.warning(request, _("You must fill the name and upload a signed file to proceed"))

    except ValidationError, e:
        for msg in e.messages:
            messages.error(request, msg, fail_silently=True)
    except PermissionDenied, e:
        messages.error(request, _("Permission denied: %s") % e, fail_silently=True)
        return redirect('inventory_view', object_id=object_id)
    except subprocess.CalledProcessError, e:
        messages.error(request, _("The uploaded signature file does not contain a valid signature"), fail_silently=True)
    except ObjectDoesNotExist, e:
        messages.error(request, _("Incorrect role or department to validate inventory: %s") % e, fail_silently=True)

    # else, if no form posted:
    return render_to_response('inventory_validate_ask.html',
        { 'object': inventory, 'form': form },
        context_instance=RequestContext(request))

def inventory_printout(request, object_id):
    inventory = get_object_or_404(Inventory, pk=object_id)
    from django.template.loader import render_to_string
    from rml2pdf import parseString
    logger = logging.getLogger('apps.inventory')
    logger.info("Rendering inventory #%d %s to HTTP", inventory.id, inventory.name)

    rml_str = render_to_string('inventory_list.rml.tmpl',
                dictionary={ 'object': inventory, 'report_name': 'inventory.pdf',
                        'internal_title': "Inventory %d" % inventory.id,
                        'now': datetime.datetime.now(),
                        'user': request.user,
                        'author': "Django-inventory"  } )
    outPDF = parseString(rml_str, localcontext={})
    return HttpResponse(outPDF, content_type='application/pdf')

def inventory_reject(request, object_id):
    inventory = get_object_or_404(Inventory, pk=object_id)

    data = {
        'object': inventory,
        'title':_(u"Are you sure you want to reject inventory: %s?") % inventory,
    }

    if inventory.state not in ('draft', 'pending'):
        msg = _(u'This inventory is %s, cannot reject.') % inventory.get_state_display()
        messages.error(request, msg, fail_silently=True)
        return redirect(request.META['HTTP_REFERER'] if 'HTTP_REFERER' in request.META else inventory.get_absolute_url())
    try:
        active_role = role_from_request(request)
        if not (active_role and active_role.has_perm('inventory.validate_inventory')):
            raise PermissionDenied(_("Your active role does not have permission to reject an inventory"))
        # check that active_role has the same dept as inventory!
        if active_role.department != inventory.location.department:
            raise PermissionDenied(_("You are not currently signed at the same Department as this Inventory"))
    except PermissionDenied, e:
        messages.error(request, _("Permission denied: %s") % e, fail_silently=True)
        return redirect('inventory_view', object_id=object_id)

    if request.method == 'POST':
        inventory.do_reject(request.user)
        msg = _(u'The inventory has been marked as rejected, it will no longer be used.')
        messages.success(request, msg, fail_silently=True)
        return redirect(inventory.get_absolute_url())

    return render_to_response('generic_confirm.html', data, context_instance=RequestContext(request))

#eof