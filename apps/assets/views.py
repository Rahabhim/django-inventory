# -*- encoding: utf-8 -*-
# from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404 #, redirect
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.db.models import Q, Count
from django.contrib import messages
from django.core.urlresolvers import reverse

from generic_views.views import generic_assign_remove, GenericBloatedListView

from models import Item, ItemGroup, State, ItemState

from common.models import Location
from company.models import Department
from assets import state_filter
from company import make_mv_location
from products.models import Manufacturer, ItemCategory

def manufacturer_filter_queryset(form, parent, parent_queryset):
    return Manufacturer.objects.filter(id__in=parent_queryset.order_by('item_template__id').values('item_template__manufacturer'))

manufacturer_filter = {'name':'manufacturer', 'title':_(u'manufacturer'),
            'queryset': manufacturer_filter_queryset, 'destination':'item_template__manufacturer'}

def category_filter_queryset(form, parent, parent_queryset):
    return ItemCategory.objects.filter(id__in=parent_queryset.order_by('item_template__id').values('item_template__category'))

category_filter = { 'name': 'category', 'title': _(u'category'), 'tree_by_parent': 'parent',
            'queryset': category_filter_queryset, 'destination': 'item_template__category'}

product_filter = {'name': 'product_name', 'title': _('product'),
            'destination': ('item_template__description__icontains', 'item_template__model__icontains',
                            'item_template__part_number')}

location_filter = {'name': 'location', 'title': _('location'),
            'destination': make_mv_location('location')}


def item_setstate(request, object_id, state_id):
    item = get_object_or_404(Item, pk=object_id)
    state = get_object_or_404(State, pk=state_id)

    if state.id in ItemState.objects.states_for_item(item).values_list('state', flat=True):
        messages.error(request, _(u"This asset has already been marked as '%s'.") % state.name)
        return HttpResponseRedirect(reverse("item_view", args=[item.id]))

    next = reverse("item_view", args=[item.id])
    data = {
        #'next':next,
        'object':item,
        'title':_(u"Are you sure you wish to mark this asset as '%s'?") % state.name,
    }

    if state.exclusive:
        data['message'] = _(u"Any other states this asset may be marked as, will be cleared.")


    if request.method == 'POST':
        if state.exclusive:
            for item_state in ItemState.objects.states_for_item(item):
                item_state.delete()
        else:
            exclusive_state = ItemState.objects.states_for_item(item).filter(state__exclusive=True)
            if exclusive_state:
                messages.error(request, _(u"This asset has already been exclusively marked as '%s'.  Clear this state first.") % exclusive_state[0].state.name)
                return HttpResponseRedirect(reverse("item_view", args=[item.id]))


        new = ItemState(item=item, state=state)
        new.save()

        messages.success(request, _(u"The asset has been marked as '%s'.") % state.name)

        return HttpResponseRedirect(next)

    return render_to_response('generic_confirm.html', data,
    context_instance=RequestContext(request))


def item_remove_state(request, object_id, state_id):
    item = get_object_or_404(Item, pk=object_id)
    state = get_object_or_404(State, pk=state_id)
    next = reverse("item_view", args=[item.id])

    item_state = ItemState.objects.filter(item=item, state=state)
    if not item_state:
        messages.error(request, _(u"This asset is not marked as '%s'") % state.name)
        return HttpResponseRedirect(next)

    data = {
        #'next':next,
        'object':item,
        'title':_(u"Are you sure you wish to unmark this asset as '%s'?") % state.name,
    }
    if request.method == 'POST':
        if item_state:
            try:
                item_state.delete()
                messages.success(request, _(u"The asset has been unmarked as '%s'.") % state.name)
            except:
                messages.error(request, _(u"Unable to unmark this asset as '%s'") % state.name)

        return HttpResponseRedirect(next)

    return render_to_response('generic_confirm.html', data,
    context_instance=RequestContext(request))


def group_assign_remove_item(request, object_id):
    obj = get_object_or_404(ItemGroup, pk=object_id)

    return generic_assign_remove(
        request,
        title=_(u'Assign assets to the group: <a href="%(url)s">%(obj)s</a>' % {'url':obj.get_absolute_url(), 'obj':obj}),
        obj=obj,
        left_list_qryset=Item.objects.exclude(itemgroup=obj),
        right_list_qryset=obj.items.all(),
        add_method=obj.items.add,
        remove_method=obj.items.remove,
        left_list_title=_(u"Unassigned assets"),
        right_list_title=_(u"Assigned assets"),
        item_name=_(u"assets"),
        list_filter=[location_filter])


class AssetListView(GenericBloatedListView):
    """ The default Assets view
    
        It is merely a BloatedListView, configured with all settings about assets
    """
    title = None
    queryset=Item.objects.by_request
    list_filters=[ product_filter, manufacturer_filter, category_filter,
                            location_filter, state_filter]
    url_attribute='get_details_url'
    prefetch_fields=('item_template', 'item_template.category', 'item_template.manufacturer')
    group_by='item_template'
    group_fields=[ dict(name=_(u'Item Template'), colspan=2),
                    dict(name=_(u'Manufacturer'), attribute='manufacturer', order_attribute='manufacturer.name'),
                    dict(name=_(u'Category'), attribute='category', order_attribute='category.name'),]
    extra_columns=[ dict(attribute='get_specs', name=_(u'specifications'), under='id'),
                            dict(name=_('Serial number'), attribute='serial_number'),
                            dict(name=_('Location'), attribute='location'),
                            ]

class LocationAssetsView(AssetListView):
    extra_columns=[ dict(attribute='get_specs', name=_(u'specifications'), under='id'),
                            dict(name=_('Serial number'), attribute='serial_number'),
                  ]
    def get(self, request, loc_id, **kwargs):
        location = get_object_or_404(Location, pk=loc_id)
        self.title = _(u"location assets: %s") % location
        self.queryset = Item.objects.filter(location=location)
        return super(LocationAssetsView, self).get(request, **kwargs)

class DepartmentAssetsView(AssetListView):
    extra_columns=[ dict(attribute='get_specs', name=_(u'specifications'), under='id'),
                            dict(name=_('Serial number'), attribute='serial_number'),
                  ]
    def get(self, request, dept_id, **kwargs):
        department = get_object_or_404(Department, pk=dept_id)
        self.title = _(u"department assets: %s") % department
        self.queryset = Item.objects.filter(location__department=department)
        return super(DepartmentAssetsView, self).get(request, **kwargs)

#eof
