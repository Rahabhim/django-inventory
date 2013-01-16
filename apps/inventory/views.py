# -*- encoding: utf-8 -*-

from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
# from django.contrib.contenttypes.models import ContentType
from django.views.generic.list_detail import object_detail, object_list
# from django.core.urlresolvers import reverse
from django.db.models import Q, Count
#from generic_views.views import generic_assign_remove, generic_list

#from photos.views import generic_photos

from common.models import Supplier
from assets.models import Item, ItemGroup

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
        
        items_in_inventory = [ ii.asset_id for ii in inventory.items.all()]
        res = []
        items_base = Item.objects.filter(Q(pk__in=items_in_inventory)|Q(location=inventory.location)).order_by('id')

        items_in_inventory = set(items_in_inventory)
        have_pending = False
        found = True
        while found and len(res) < limit:
            found = False
            for item in items_base[offset:offset+limit]:
                found = True
                if item.id not in items_in_inventory:
                    res.append((item, 'new'))
                    have_pending = True
                elif item.location_id != inventory.location_id:
                    res.append((item, 'missing'))
                    have_pending = True
                elif not pending_only:
                    res.append((item, 'ok'))
            offset += limit
        if res:
            subtemplates_dict.append({ 'name':'inventory_items_compare.html',
                            'object_list': res, })

        if not (have_pending or pending_only):
            # We must search the full set about wrong items
            print "compute again"
            items_mismatch = Item.objects.filter( \
                    (Q(pk__in=items_in_inventory) & ~Q(location=inventory.location)) | \
                    (Q(location=inventory.location) & ~Q(pk__in=items_in_inventory)) ).exists()

            print "items mismatch", items_mismatch
            if items_mismatch:
                have_pending = True

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
'''
def item_log_list(request, object_id):
    item = Item.objects_passthru.get(pk=object_id)
    ctype = ContentType.objects.get_for_model(item)
    log=Log.objects.filter(content_type__pk=ctype.id, object_id=item.id)
    return object_list(
        request,
        queryset=log,
        template_name='generic_list.html',
        extra_context={'title':_(u"Asset log: %s") % item},
        )

'''
'''
def render_to_pdf(template_src, context_dict):
    from django import http
    from django.shortcuts import render_to_response
    from django.template.loader import get_template
    from django.template import Context
    import ho.pisa as pisa
    import cStringIO as StringIO
    import cgi

    template = get_template(template_src)
    context = Context(context_dict)
    html  = template.render(context)
    result = StringIO.StringIO()
    pdf = pisa.pisaDocument(StringIO.StringIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return http.HttpResponse(result.getvalue(), mimetype='application/pdf')
    return http.HttpResponse('We had some errors<pre>%s</pre>' % cgi.escape(html))

def report_items_per_person(request, object_id):
    person = Person.objects.get(pk=object_id)

    return render_to_pdf('report-items_per_person.html',
#	return render_to_response('report-items_per_person.html',
        {
            'pagesize':'A4',
            'object': person
        })

'''
