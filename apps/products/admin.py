from django.contrib import admin
from models import ItemTemplate

class ItemTemplateAdmin(admin.ModelAdmin):
    filter_horizontal = ('supplies', 'suppliers')

admin.site.register(ItemTemplate, ItemTemplateAdmin)

#eof
