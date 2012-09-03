from django.conf.urls.defaults import patterns, url
from django.contrib import admin

from django.views.generic.create_update import create_object, update_object

from generic_views.views import generic_assign_remove, \
                                generic_delete, \
                                generic_detail, generic_list

"""

admin?

TODO
"""

def auto_urls(*models):
    """Automatically create standard URLs and actions for model(s)
    
        objects/create/<obj>
        objects/list/<model>
        objects/form/<model>-<id>
        objects/update/<model>-<id>
        objects/delete/<model>-<id>
    
    """
    
    upats = []
    
    for model in models:
        mmeta = model._meta
        # let's see what this model allows us to do
        
        
        if True : #  'r' in perms:
            upats.append(url(r'objects/list/' + mmeta.db_table, \
                    generic_list, kwargs=dict(queryset=model.objects.all(), extra_context={}),
                    name=mmeta.db_table+"_list"
                    ))

    return patterns('', *upats)

def auto_admin(*models):
    """ Automatically add models to admin site
    """
    for model in models:
        mmeta = model._meta
        ## let's see what this model allows us to do
        #perms = getattr(mmeta, '_permissions', 'ar')
        
        if True: #  'a' in perms:
            admin.site.register(model)
    return


#eof
