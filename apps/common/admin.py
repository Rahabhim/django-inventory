from django.contrib import admin
from models import Location, LocationTemplate, Partner, Supplier
from ajax_select import make_ajax_form
from ajax_select.admin import AjaxSelectAdmin

class LocationAdmin(AjaxSelectAdmin):
    form = make_ajax_form(Location, dict(department='department'))

admin.site.register(Location, LocationAdmin)
admin.site.register(LocationTemplate)
admin.site.register(Partner)
admin.site.register(Supplier)


