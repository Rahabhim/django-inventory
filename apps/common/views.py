# -*- encoding: utf-8 -*-
from django.shortcuts import get_object_or_404, redirect
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from django.contrib import messages

from generic_views.views import GenericBloatedListView

from models import Location, LocationTemplate

from common.api import role_from_request
from company.models import Department
from company.lookups import _department_filter_q

name_filter = {'name': 'name', 'title': _("name"), 'destination': 'name__contains' }

location_dept_filter = {'name': 'dept', 'title': _('department'), 
            'destination': lambda q: Q(department__in=Department.objects.filter(_department_filter_q(q)))}

usage_filter = {'name': 'usage', 'title': _("location type"), 'destination': 'usage',
            'choices':'common.Location.usage' , }

template_filter = {'name': 'template', 'title': _("Type of template"), 'destination': 'template',
            'queryset': LocationTemplate.objects.filter(sequence__lt=100), }

class LocationListView(GenericBloatedListView):
    queryset=Location.objects.all()  # TODO: by request?
    list_filters=[location_dept_filter, name_filter, template_filter, usage_filter]
    extra_columns=[ {'name': _(u'active'), 'attribute': 'fmt_active'},
                    {'name': _('Type'), 'attribute': 'template'}, ]
    prefetch_fields=('department',)
    extra_context=dict(title =_(u'locations'))

class DepartmentLocationsView(LocationListView):
    def get(self, request, dept_id, **kwargs):
        department = get_object_or_404(Department, pk=dept_id)
        self.title = _(u"locations of %s") % department
        self.queryset = Location.objects.filter(department=department)
        self.dept_id = dept_id
        return super(DepartmentLocationsView, self).get(request, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super(DepartmentLocationsView, self).get_context_data(**kwargs)
        ctx['department'] = Department.objects.get(pk=self.dept_id)
        return ctx


def location_do_activate(request, object_id):
    """Sets the Location to active
    """
    location = get_object_or_404(Location, pk=object_id)
    active_role = role_from_request(request)
    if request.user.is_superuser:
        pass
    elif not (active_role and active_role.has_perm('common.locations_edit_active')):
        raise PermissionDenied
    if not location.active:
        location.active = True
        messages.info(request, _("Location %s has been activated") % location.name)
        location.save()

    if 'HTTP_REFERER' in request.META:
        return redirect(request.META['HTTP_REFERER'])
    else:
        return redirect('department_locations', dept_id=location.department.id)

def location_do_deactivate(request, object_id):
    """Sets the Location to inactive, checks assets there
    """
    from assets.models import Item

    location = get_object_or_404(Location, pk=object_id)
    active_role = role_from_request(request)
    if request.user.is_superuser:
        pass
    elif not (active_role and active_role.has_perm('common.locations_edit_active')):
        raise PermissionDenied

    if Item.objects.filter(location=location).exists():
        messages.error(request, _("Location contains assets, cannot deactivate"))
    elif location.active:
        location.active = False
        messages.info(request, _("Location %s has been deactivated") % location.name)
        location.save()

    if 'HTTP_REFERER' in request.META:
        return redirect(request.META['HTTP_REFERER'])
    else:
        return redirect('department_locations', dept_id=location.department.id)

#eof
