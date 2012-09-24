from django.contrib import admin

from models import State, ItemState, Item, ItemGroup

admin.site.register(State)
admin.site.register(ItemState)
admin.site.register(Item)
admin.site.register(ItemGroup)
