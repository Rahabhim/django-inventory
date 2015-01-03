# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models

from django.http import HttpResponseForbidden
from models import Department
from common.api import LookupChannel

class DepartmentLookup(LookupChannel):
    model = Department
    search_field = 'name'

#eof
