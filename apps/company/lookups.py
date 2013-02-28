# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models
from django.http import HttpResponseForbidden
from models import Department
from common.models import Location
from common.api import LookupChannel, role_from_request

def _departments_by_q(q):
    return Department.objects.filter(_department_filter_q(q))

def _department_filter_q(q):
    """Select departments that match search `q`
    
        We have too many departments, so this search must be smart enough.
        The convention is that we use spaces in the search, meaning that
        all parts of the query string must be contained. Additionally, a
        number will only match an exact number (not partial) at the beginning
        of the name.
        Eg:
           q="ales"  return = ["Sales", "Males", "Ales"]
           q="ent ales" return= ["Enterprize Sales",]
           q="ales 10" return=["10 Sales",] not ["110 Sales", "Sales 10"]
        
        @param qset If given, the base Department.objects queryset to start from
    """
    filters = []
    for r in q.split(' '):
        if r.isdigit():
            filters.append(models.Q(name__regex=r'^%s[^0-9]' % r))
        else:
            filters.append(models.Q(name__icontains=r))
    
    if not filters:
        return models.Q()
    return reduce(lambda a, b: a & b, filters)

class DepartmentLookup(LookupChannel):
    model = Department
    # search_field = 'name'

    def get_query(self,q,request):
        """ Query the departments for a name containing `q`
        """
        if not request.user.is_authenticated():
            raise HttpResponseForbidden()
        # filtering only this user's contacts
        return _departments_by_q(q)[:100]

class LocationLookup(LookupChannel):
    model = Location

    def get_query(self, q, request):
        return Location.objects.filter(models.Q(department__in=_departments_by_q(q))| \
                    models.Q(department=None, name__icontains=q)).\
                order_by('department__name', 'name')[:20]

class RoleLocationLookup(LookupChannel):
    """ Only lookup the Locations under the active role's Department
    """
    model = Location

    def get_query(self, q, request):
        active_role = role_from_request(request)
        loc_list = None
        if request.user.is_staff:
            # search for term in all departments' names, or in location name
            loc_list =  Location.objects.filter(models.Q(department__in=_departments_by_q(q))| \
                    models.Q(department=None, name__icontains=q))
        elif active_role:
            # search for term in all departments the user has access to
            loc_list = Location.objects.filter(department=active_role.department, name__icontains=q) \
                    .filter(models.Q(department__in=_departments_by_q(q))| models.Q(department=None, name__icontains=q))
        else:
            # search for term in the locations of the current department
            loc_list = Location.objects.filter(department__in=request.user.dept_roles.values_list('department', flat=True))

        return loc_list.order_by('name')[:20]

#eof
