from django.contrib import admin
from models import ItemTemplate, ItemCategory, Manufacturer, ProductAttribute

class ItemTemplateAdmin(admin.ModelAdmin):
    filter_horizontal = ('supplies', 'suppliers')

admin.site.register(ItemTemplate, ItemTemplateAdmin,)
admin.site.register(ItemCategory)
admin.site.register(ProductAttribute)
admin.site.register(Manufacturer)

#eof
