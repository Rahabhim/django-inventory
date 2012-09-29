# -*- encoding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.views.generic.list_detail import object_detail, object_list
from generic_views.views import generic_assign_remove, generic_list

from common.models import Supplier
from models import ItemTemplate

def template_items(request, object_id):
    template = get_object_or_404(ItemTemplate, pk=object_id)
    return object_list(
        request,
        queryset = template.item_set.all(),
        template_name = "generic_list.html",
        extra_context=dict(
            title = '%s: %s' % (_(u"assets that use the template"), template),
        ),
    )


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
        left_list_qryset=ItemTemplate.objects.exclude(supplies=obj).exclude(pk=obj.pk),
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
