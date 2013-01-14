# -*- encoding: utf-8 -*-
import copy
import ajax_select
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden

object_navigation = {}
menu_links = []

def register_links(src, links, menu_name=None):
    if menu_name in object_navigation:
        if hasattr(src, '__iter__'):
            for one_src in src:
                if one_src in object_navigation[menu_name]:
                    object_navigation[menu_name][one_src]['links'].extend(links)
                else:
                    object_navigation[menu_name][one_src]={'links':copy.copy(links)}
        else:
            if src in object_navigation[menu_name]:
                object_navigation[menu_name][src]['links'].extend(links)
            else:
                object_navigation[menu_name][src] = {'links':links}
    else:
        object_navigation[menu_name] = {}
        if hasattr(src, '__iter__'):
            for one_src in src:
                object_navigation[menu_name][one_src] = {'links':links}
        else:
            object_navigation[menu_name] = {src:{'links':links}}


def register_menu(links):
    for link in links:
        menu_links.append(link)

    menu_links.sort(lambda x,y: 1 if x>y else -1, lambda x:x['position'] if 'position' in x else 1)

def register_submenu(menu_id, links):
    """ Adds some more links to existing menu

        Useful for foreign applications to append a base menu
        @param menu_id  shall match the 'id' field of a menu entry
        @param links    list of links to append to menu's links
    """
    for ml in menu_links:
        if ml.get('id', False) == menu_id:
            ml.setdefault('links', []).extend(links)
            break
    else:
        raise KeyError("No menu with id: %s" % menu_id)

class LookupChannel(ajax_select.LookupChannel):
    max_length = 50

    def check_auth(self,request):
        if not request.user.is_authenticated():
            raise PermissionDenied()
        return True

    def get_query(self,q,request):
        """ Query the departments for a name containing `q`
        """
        if not request.user.is_authenticated():
            raise HttpResponseForbidden()
        # filtering only this user's contacts
        cur = self.model.objects
        for r in q.split(' '):
            cur = cur.filter(**{"%s__icontains" % self.search_field: r})
        return cur.order_by(self.search_field)[:self.max_length]

# Condition functions for the views

def _user_has_perm(user, obj, pattern):
    """Assert that user has permission as in `pattern` on object
    """
    try:
        npd = {'app': obj._meta.app_label, 'Model': obj._meta.object_name,
                'model': obj._meta.module_name}
        return user.has_perm(pattern % npd)
    except Exception, e:
        return False

def can_add(model):
    """ Return a function to test user's permission to create model
    
        Since the "create" link will exist in the "list" view, no object
        will be available.
    """
    return lambda obj, context: _user_has_perm(context['user'], model, '%(app)s.add_%(model)s')

def can_edit(obj, context):
    """ Assert if current user can edit the model of `obj`
    """
    return _user_has_perm(context['user'], obj, '%(app)s.change_%(model)s')

def can_delete(obj, context):
    """ Assert if current user can edit the model of `obj`
    """
    return _user_has_perm(context['user'], obj, '%(app)s.delete_%(model)s')

#eof

