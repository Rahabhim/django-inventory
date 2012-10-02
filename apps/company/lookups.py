# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models

from django.http import HttpResponseForbidden
from models import Department
from common.models import Location
from ajax_select import LookupChannel

class DepartmentLookup(LookupChannel):
    model = Department
    search_field = 'name'

class LocationLookup(LookupChannel):
    model = Location

    def get_query(self, q, request):
        # FIXME use Department algo
        return Location.objects.filter(department__name__icontains=q).\
                order_by('department__name', 'name')[:20]

#eof
