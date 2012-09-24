# from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404 #, redirect
from django.template import RequestContext
from django.utils.translation import ugettext as _
# from django.db.models import Q
from django.contrib import messages
# from django.contrib.contenttypes.models import ContentType
from django.views.generic.list_detail import object_list # object_detail,
from django.core.urlresolvers import reverse

from generic_views.views import generic_assign_remove #, generic_list

from common import location_filter

from models import Item, ItemGroup, State, ItemState



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


#eof
