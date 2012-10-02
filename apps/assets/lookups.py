# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models

from django.http import HttpResponseForbidden
from models import Item
from ajax_select import LookupChannel

class ItemLookup(LookupChannel):
    model = Item
    search_field = 'item_template__description' ## FIXME: use serial, too...

#eof