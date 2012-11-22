# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models

from django.http import HttpResponseForbidden
from models import Item
from common.api import LookupChannel

class ItemLookup(LookupChannel):
    model = Item
    search_field = 'item_template__description'
    def get_query(self, q, request):
        if not request.user.is_authenticated():
            raise HttpResponseForbidden()

        cur = self.model.objects
        filt = models.Q(property_number=q)|models.Q(serial_number=q)
        if cur.filter(filt).exists():
            # only those who match exact the property/serial
            return cur.filter(filt)

        for r in q.split(' '):
            cur = cur.filter(**{"%s__icontains" % self.search_field: r})
        return cur[:self.max_length]

#eof