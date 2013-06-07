# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2013
# Only a few rights reserved

#from django.db import models

#from django.http import HttpResponse
from models import Supplier
from django.utils.html import escape
from common.api import LookupChannel

class SupplierLookup(LookupChannel):
    model = Supplier
    search_field = 'name'
    queryset = Supplier.objects.filter(active=True)

class SupplierVATLookup(LookupChannel):
    """Locate supplier by VAT number (exact match)
    """
    model = Supplier
    plugin_options = {'min_length':  9 }

    def get_query(self, q, request):
        return self.model.objects.filter(active=True, vat_number=q)[:self.max_length]

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self,obj):
        """format the output including VAT
        """
        # TODO: use styles etc. for VAT field.
        return u"%s, %s" % (escape(obj.vat_number), escape(obj.name))
#eof
