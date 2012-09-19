from django.contrib import admin
from models import ItemTemplate, ItemCategory, ItemAttrType, Manufacturer

class ItemTemplateAdmin(admin.ModelAdmin):
    filter_horizontal = ('supplies', 'suppliers')

admin.site.register(ItemTemplate, ItemTemplateAdmin,)
admin.site.register(ItemCategory)
admin.site.register(ItemAttrType)
admin.site.register(Manufacturer)

#eof
