# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models

from django.http import HttpResponseForbidden
from models import ItemTemplate, Manufacturer
from ajax_select import LookupChannel

class ItemTemplateLookup(LookupChannel):
    model = ItemTemplate
    search_field = 'description'

class ManufacturerLookup(LookupChannel):
    model = Manufacturer
    search_field = 'name'

#eof
