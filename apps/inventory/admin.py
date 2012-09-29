# -*- encoding: utf-8 -*-
from django.contrib import admin

from inventory.models import Log, Inventory

admin.site.register(Log)
admin.site.register(Inventory)


