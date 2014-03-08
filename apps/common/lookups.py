# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2013-2014
# Only a few rights reserved

from django.db.models import Q

#from django.http import HttpResponse
from models import Supplier
from django.utils.html import escape
from common.api import LookupChannel

class SupplierLookup(LookupChannel):
    model = Supplier
    search_field = 'name'
    queryset = Supplier.objects.filter(active=True)

class SupplierVATLookup(LookupChannel):
    """Locate supplier by name or VAT number (exact match)
    """
    model = Supplier
    plugin_options = {'min_length':  2}
    queryset = Supplier.objects.filter(active=True)

    def get_query(self, q, request):
        aq = Q(name__icontains=q)
        if q and len(q) >= 9 and q.isdigit():
            aq = aq | Q(vat_number=q)
        return self.queryset.filter(aq)[:self.max_length]

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self,obj):
        """format the output including VAT
        """
        if obj.vat_number:
            return u"%s [%s]" % (escape(obj.name), escape(obj.vat_number))
        else:
            return escape(obj.name)
#eof
