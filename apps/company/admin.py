# -*- encoding: utf-8 -*-
from django.contrib import admin
from models import DepartmentType, Department, DepartmentLocTemplates
from ajax_select import make_ajax_form
from ajax_select.admin import AjaxSelectAdmin

class DepartmentAdmin(AjaxSelectAdmin):
    form = make_ajax_form(Department, { 'parent':'department', 
                        'serviced_by': 'department', 'merge': 'department'})

admin.site.register(Department, DepartmentAdmin)

class DepartmentLocTemplatesInline(admin.TabularInline):
    model = DepartmentLocTemplates
    extra = 1

class DeptTypeAdmin(admin.ModelAdmin):
    inlines = (DepartmentLocTemplatesInline,)

    class Media:
        js = ( 'js/inlines.js',)

admin.site.register(DepartmentType, DeptTypeAdmin)
#eof