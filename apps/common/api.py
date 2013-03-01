import copy

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

#eof
