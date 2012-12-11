# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models

from django.http import HttpResponseForbidden
from models import Contract
from common.api import LookupChannel

class ContractLookup(LookupChannel):
    model = Contract
    search_field = 'name'


#eof