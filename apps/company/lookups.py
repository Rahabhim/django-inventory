# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models

from django.http import HttpResponseForbidden
from models import Department
from common.models import Location
from ajax_select import LookupChannel

def _departments_by_q(q):
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
    """
    qset = Department.objects
    for r in q.split(' '):
        if r.isdigit():
            qset = qset.filter(name__regex=r'^%s[^0-9]' % r)
        else:
            qset = qset.filter(name__icontains=r)
    return qset

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

#eof
