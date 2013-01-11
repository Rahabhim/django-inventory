from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from ajax_select.fields import AutoCompleteSelectField

from models import UserProfile

# Define an inline admin descriptor for UserProfile model
# which acts a bit like a singleton
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'
    raw_id_fields = ('department',)
    
    class Media:
        js = ( 'js/ajax_select.js',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'department':
            return AutoCompleteSelectField('department', required=False, **kwargs)
        return super(UserProfileInline, self).formfield_for_foreignkey(db_field, request, **kwargs)

# Define a new User admin
class UserAdmin(UserAdmin):
    inlines = (UserProfileInline, )
    class Media:
        js = ('js/inlines.min.js', )

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

#eof