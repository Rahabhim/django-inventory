# -*- encoding: utf-8 -*-
# from django.http import HttpResponse
import logging
import datetime
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404 #, redirect
from django.core.exceptions import PermissionDenied
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
#from django.db.models import Q, Count
from django.contrib import messages
from django.core.urlresolvers import reverse

from generic_views.views import GenericBloatedListView

from models import Item, State, ItemState

from common.models import Location
from common.api import role_from_request
from company.models import Department
from assets import state_filter
from company import make_mv_location
from products.models import Manufacturer, ItemCategory, ItemTemplate
#from procurements.models import Contract

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
                            'item_template__part_number', 'serial_number', 'property_number')}

location_filter = {'name': 'location', 'title': _('location'),
            'destination': make_mv_location('location')}

contract_filter = { 'name': 'contract', 'lookup_channel': 'contracts', 'title': _('procurement contract'),
            'destination': 'src_contract'}

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

class AssetListView(GenericBloatedListView):
    """ The default Assets view
    
        It is merely a BloatedListView, configured with all settings about assets
    """
    template_name = 'assets_list.html'
    queryset=Item.objects.by_request
    list_filters=[ product_filter, manufacturer_filter, category_filter,
                            location_filter, state_filter, contract_filter]
    url_attribute='get_details_url'
    prefetch_fields=('item_template', 'item_template.category', 'item_template.manufacturer', 'src_contract.name')
    group_by='item_template'
    group_fields=[ dict(name=_(u'Item Template'), colspan=4),
                    dict(name=_(u'Manufacturer'), attribute='manufacturer', order_attribute='manufacturer.name', over="item_template"),
                    dict(name=_(u'Category'), attribute='category', order_attribute='category.name', over="item_template"),
                ]
    extra_columns=[ # dict(attribute='get_specs', name=_(u'specifications'), under='id'),
                            dict(name=_('Serial number'), attribute='serial_number'),
                            dict(name=_('Location'), attribute='location'),
                            dict(name=_('Source Contract'), attribute='src_contract'),
                            ]

class LocationAssetsView(AssetListView):
    extra_columns=[ # dict(attribute='get_specs', name=_(u'specifications'), under='id'),
                            dict(name=_('Serial number'), attribute='serial_number'),
                            dict(name=_('Source Contract'), attribute='src_contract'),
                  ]
    def get(self, request, loc_id, **kwargs):
        location = get_object_or_404(Location, pk=loc_id)
        if not (request.user.is_staff or location.department_id):
            raise PermissionDenied
        self.title = _(u"location assets: %s") % location
        self.queryset = Item.objects.filter(location=location)
        return super(LocationAssetsView, self).get(request, **kwargs)

class DepartmentAssetsView(AssetListView):
    extra_columns=[ dict(attribute='get_specs', name=_(u'specifications'), under='id'),
                            dict(name=_('Serial number'), attribute='serial_number'),
                            dict(name=_('Source Contract'), attribute='src_contract'),
                  ]
    def get(self, request, dept_id, **kwargs):
        department = get_object_or_404(Department, pk=dept_id)
        self.title = _(u"department assets: %s") % department
        self.queryset = Item.objects.filter(location__department=department)
        self.dept_id = dept_id
        return super(DepartmentAssetsView, self).get(request, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super(DepartmentAssetsView, self).get_context_data(**kwargs)
        ctx['department'] = Department.objects.get(pk=self.dept_id)
        return ctx

class TemplateAssetsView(AssetListView):
    list_filters=[ location_filter, state_filter, contract_filter]
    prefetch_fields=( 'src_contract.name', )
    group_by='src_contract'
    # problem: if there is no source contract, entries will be hidden :(
    group_fields=[ dict(name=_(u'Source Contract'), colspan=2), ]
    extra_columns=[ # dict(attribute='get_specs', name=_(u'specifications'), under='id'),
                            dict(name=_('Serial number'), attribute='serial_number'),
                            dict(name=_('Location'), attribute='location'),
                            ]

    def get(self, request, product_id, **kwargs):
        template = get_object_or_404(ItemTemplate, pk=product_id)
        self.title = _(u"Items of template: %s") % template
        self.queryset = self.queryset(request).filter(item_template=template)
        return super(TemplateAssetsView, self).get(request, **kwargs)

def asset_printout(request, object_id):
    asset = get_object_or_404(Item, pk=object_id)
    if not request.user.is_staff:
        # don't allow other roles to see assets of another dept.
        active_role = role_from_request(request)
        if active_role and asset.location.department in active_role.departments:
            pass
        else:
            raise PermissionDenied

    from django.template.loader import render_to_string
    from rml2pdf import parseString
    logger = logging.getLogger('apps.assets')
    logger.info("Rendering asset #%d %s to HTTP", asset.id, asset.property_number)

    rml_str = render_to_string('asset_details.rml.tmpl',
                dictionary={ 'object': asset, 'report_name': 'asset-%d.pdf' % asset.id,
                        'internal_title': "Asset %d" % asset.id,
                        'now': datetime.datetime.now(),
                        'user': request.user,
                        'author': "Django-inventory"  } )
    outPDF = parseString(rml_str, localcontext={})
    return HttpResponse(outPDF, content_type='application/pdf')

def asset_list_printout(request, dept_id):
    dept = get_object_or_404(Department, pk=dept_id)
    if not request.user.is_staff:
        # don't allow other roles to see assets of another dept.
        active_role = role_from_request(request)
        if active_role and dept in active_role.departments:
            pass
        else:
            raise PermissionDenied

    from django.template.loader import render_to_string
    from rml2pdf import parseString
    logger = logging.getLogger('apps.assets')
    logger.info("Rendering department #%d %s asset list to HTTP", dept.id, dept.name)

    def locations():
        for loc in Location.objects.filter(department=dept).all():
            assets = Item.objects.filter(location=loc, active=True)
            yield loc, assets

    rml_str = render_to_string('asset_list.rml.tmpl',
                dictionary={ 'object': dept, 'report_name': 'department-%d-assets.pdf' % dept.id,
                        'internal_title': "Department %d" % dept.id,
                        'now': datetime.datetime.now(),
                        'user': request.user,
                        'author': "Django-inventory",
                        'locations': locations,
                        } )
    outPDF = parseString(rml_str, localcontext={})
    return HttpResponse(outPDF, content_type='application/pdf')

def asset_list_printout2(request):
    active_role = role_from_request(request)
    if active_role.department:
        return HttpResponseRedirect(reverse("asset_list_printout", args=[active_role.department.id]))
    else:
        raise PermissionDenied

#eof
