# -*- encoding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404
from generic_views.views import generic_assign_remove
from django.http import HttpResponse, HttpResponseNotAllowed
from django.utils import simplejson

from common.models import Supplier
from models import ItemTemplate, ItemCategory, ProductAttributeValue


def supplier_assign_remove_itemtemplates(request, object_id):
    obj = get_object_or_404(Supplier, pk=object_id)

    return generic_assign_remove(
        request,
        title=_(u'Assign templates to the supplier: <a href="%(url)s">%(obj)s</a>' % {'url':obj.get_absolute_url(), 'obj':obj}),
        obj=obj,
        left_list_qryset=ItemTemplate.objects.exclude(suppliers=obj),
        right_list_qryset=obj.itemtemplate_set.all(),
        add_method=obj.itemtemplate_set.add,
        remove_method=obj.itemtemplate_set.remove,
        left_list_title=_(u'Unassigned templates'),
        right_list_title=_(u'Assigned templates'),
        item_name=_(u"templates"),
    )

def template_assign_remove_supply(request, object_id):
    obj = get_object_or_404(ItemTemplate, pk=object_id)


    return generic_assign_remove(
        request,
        title=_(u'Assign supplies to the template: <a href="%(url)s">%(obj)s</a>' % {'url':obj.get_absolute_url(), 'obj':obj}),
        obj=obj,
        left_list_qryset=ItemTemplate.objects.filter(category__in= \
                    [mc.category for mc in obj.category.may_contain.all()])
                .exclude(supplies=obj).exclude(pk=obj.pk),
        right_list_qryset=obj.supplies.all(),
        add_method=obj.supplies.add,
        remove_method=obj.supplies.remove,
        left_list_title=_(u'Unassigned supplies'),
        right_list_title=_(u'Assigned supplies'),
        item_name=_(u"supplies"))


def template_assign_remove_suppliers(request, object_id):
    obj = get_object_or_404(ItemTemplate, pk=object_id)

    return generic_assign_remove(
        request,
        title=_(u'Assign suppliers to the template: <a href="%(url)s">%(obj)s</a>' % {'url':obj.get_absolute_url(), 'obj':obj}),
        obj=obj,
        left_list_qryset=Supplier.objects.exclude(itemtemplate=obj),
        right_list_qryset=obj.suppliers.all(),
        add_method=obj.suppliers.add,
        remove_method=obj.suppliers.remove,
        left_list_title=_(u'Unassigned suppliers'),
        right_list_title=_(u'Assigned suppliers'),
        item_name=_(u"suppliers"))

def product_combi_attrs(request):
    """Retrieve possible values for product attributes, limited to some combination
    """
    if request.method == "GET":
        params = request.GET
    elif request.method == "POST":
        params = request.POST
    else:
        return HttpResponseNotAllowed(['POST', 'GET'])

    categ = get_object_or_404(ItemCategory, pk=int(params['category']))

    products = ItemTemplate.objects.filter(category=categ)
    if params.get('manufacturer', False):
        products = products.filter(manufacturer_id=int(params['manufacturer']))

    attrs = params.getlist('attributes') or params.getlist('attributes[]') or []
    for att in attrs:
        if not att:
            continue
        products = products.filter(attributes__value_id=int(att))

    results = {}
    for cat in categ.attributes.all():
        results[cat.id] = []

    for aval in ProductAttributeValue.objects\
            .filter(itemtemplateattributes__template__in=products) \
            .distinct().prefetch_related('atype'):
        if aval.atype_id not in results:
            continue
        if str(aval.id) in attrs:
            del results[aval.atype_id]
        else:
            results[aval.atype_id].append([aval.id, aval.value])

    return HttpResponse(simplejson.dumps(results), mimetype='application/javascript')

#eof
