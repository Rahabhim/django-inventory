# -*- encoding: utf-8 -*-
from django.contrib import admin
from ajax_select import make_ajax_form
from ajax_select.admin import AjaxSelectAdmin

from inventory.models import Log, Inventory, InventoryItem

class InventoryAdmin(AjaxSelectAdmin):
    form = make_ajax_form(Inventory, dict(location='location'))

class InventoryItemAdmin(AjaxSelectAdmin):
    form = make_ajax_form(InventoryItem, dict(asset='item'))

admin.site.register(Log)
admin.site.register(Inventory, InventoryAdmin)
admin.site.register(InventoryItem, InventoryItemAdmin)

#eof
