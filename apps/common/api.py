# -*- encoding: utf-8 -*-
import copy
import re
import ajax_select
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from settings import DATE_FMT_FORMAT

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
    _white_re = re.compile(r'\s+')
    queryset = None

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
        if self.queryset is None:
            cur = self.model.objects
        else:
            cur = self.queryset
        for r in q.split(' '):
            cur = cur.filter(**{"%s__icontains" % self.search_field: r})
        return cur.order_by(self.search_field)[:self.max_length]

    def format_item_display(self,obj):
        res = super(LookupChannel, self).format_item_display(obj)
        return self._white_re.sub(' ', res)

# Condition functions for the views

def _context_has_perm(context, obj, pattern):
    """Assert that user has permission as in `pattern` on object
    """
    try:
        npd = {'app': obj._meta.app_label, 'Model': obj._meta.object_name,
                'model': obj._meta.module_name}
        role = False
        if 'request' in context:
            role = role_from_request(context['request'])
            if role.has_perm(pattern % npd):
                return True
            if context['request'].user.has_perm(pattern % npd):
                return True
        return False
    except Exception:
        return False

def can_add(model):
    """ Return a function to test user's permission to create model
    
        Since the "create" link will exist in the "list" view, no object
        will be available.
    """
    return lambda obj, context: _context_has_perm(context, model, '%(app)s.add_%(model)s')

def can_edit(obj, context):
    """ Assert if current user can edit the model of `obj`
    """
    return _context_has_perm(context, obj, '%(app)s.change_%(model)s')

def can_delete(obj, context):
    """ Assert if current user can edit the model of `obj`
    """
    return _context_has_perm(context, obj, '%(app)s.delete_%(model)s')

def user_is_staff(obj, context):
    return context['user'].is_staff

def user_is_super(obj, context):
    return context['user'].is_superuser

class _fake_role(object):
    """A fake role, for the superuser
    """
    def __init__(self, user):
        self.user = user
        self.department = None
        self.departments = []
        self.role = None

    def has_perm(self, perm):
        return True

    def __nonzero__(self):
        return False

def role_from_request(request):
    """Obtain the active DepartmentRole object from the http request

        @return True for superuser, DepartmentRole or False if no role selected
    """
    if request.user.is_superuser:
        return _fake_role(request.user)
    elif request.session.get('current_user_role', False):
        role_id = request.session['current_user_role']
        return request.user.dept_roles.get(pk=role_id)
    else:
        return False

def fmt_date(ddate):
    try:
        return ddate.strftime(DATE_FMT_FORMAT)
    except ValueError:
        # raw, ISO format
        return str(ddate)
#eof

