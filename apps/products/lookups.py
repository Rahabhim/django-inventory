# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models

from django.http import HttpResponse
from models import ItemTemplate, Manufacturer, ItemCategory
from common.api import LookupChannel

class ItemTemplateLookup(LookupChannel):
    model = ItemTemplate
    search_field = 'description'

class ItemCategoryLookup(LookupChannel):
    model = ItemCategory
    search_field = 'name'

class ManufacturerLookup(LookupChannel):
    model = Manufacturer
    search_field = 'name'

class ProductPartLookup(LookupChannel):
    """Locate product (ItemTemplate) by part number (exact match)
    """
    model = ItemTemplate

    def get_query(self, q, request):
        params = None
        if request.method == "GET":
            params = request.GET
        else:
            params = request.POST
        category = params.get('category')
        kwargs = {}
        if category:
            kwargs['category__pk'] = int(category)
        return self.model.objects.filter(approved=True, part_number=q, **kwargs)[:self.max_length]

class ProductSpecsLookup(LookupChannel):
    """Locate product by specs
    """
    model = ItemTemplate

    def get_query(self, q, request):
        """ Specs will be fed to other variables of `request` rather than `q`
        """
        cur = self.model.objects.filter(approved=True)
        params = None
        if request.method == "GET":
            params = request.GET
        else:
            params = request.POST

        manuf = params.get('manufacturer')
        attrs = params.getlist('attributes') or params.getlist('attributes[]')
        category = params.get('category')
        if not (category and (manuf or attrs)):
            # no specs, no results!
            return []
        cur = cur.filter(category=int(category))
        if manuf:
            # filter by manufacturer:
            cur = cur.filter(manufacturer__pk=int(manuf))

        if attrs:
            # filter by attributes: (all of them must be set)
            for att in attrs:
                if att:
                    cur = cur.filter(attributes__value_id=int(att))
        return cur[:self.max_length]

#eof
