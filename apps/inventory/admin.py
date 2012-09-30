# -*- encoding: utf-8 -*-
from django.contrib import admin

from inventory.models import Log, Inventory, InventoryTransaction

admin.site.register(Log)
admin.site.register(Inventory)
admin.site.register(InventoryTransaction)

#eof
