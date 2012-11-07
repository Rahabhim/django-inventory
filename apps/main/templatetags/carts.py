# -*- encoding: utf-8 -*-
from django import template
import logging
# from main import cart_utils
from django.db import models
import settings

register = template.Library()
logger = logging.getLogger('main.carts')

@register.simple_tag(takes_context=True)
def prepare_session_carts(context):
    try:
        logger.warning("Prepare session carts for context %x", id(context))
        context['carts'].load_all()

    except Exception:
        logger.warning("Cannot prepare carts:", exc_info=True)
        if settings.DEBUG:
            raise

    return ''

def cart2dict(cart):
    """Formalize the dictionary of a cart passed for rendering
    """
    return dict(title=cart.get_cart_name(), qty=cart.get_cart_itemcount(), \
                href=cart.get_cart_url(), cart_id=hex(id(cart))[-7:-1])

@register.inclusion_tag('session_carts.html', takes_context=True)
def session_carts(context):
    """Opened carts for a user session

        They should appear at the top of the menu or so.
        Also calls "prepare_session_carts"
    """
    prepare_session_carts(context)
    try:
        rcarts = context['carts']
        return {'carts': map(cart2dict, rcarts) }

    except Exception:
        logger.warning("Cannot resolve session carts:", exc_info=True)
        if settings.DEBUG:
            raise

    return {}

@register.inclusion_tag('object_carts.html', takes_context=True)
def object_carts(context, obj):
    """ Carts to appear as "actions" inside some object's line
    """
    ret = {'object': obj, 'carts': []}

    try:
        if obj is not None and isinstance(obj, models.Model):
            for cart in context['carts'].carts_for_model(obj):
                c = cart2dict(cart)
                cstate, href = cart.get_cart_objcap(obj)
                if cstate:
                    c['item_state'] = cstate
                    c['action_url'] = href + ('?item=%d' % obj.id)
                ret['carts'].append(c)

        ret['has_cart'] = bool(ret['carts'])

            # jQuery cart
    except Exception:
        logger.warning("Cannot resolve object carts:", exc_info=True)
        if settings.DEBUG:
            raise

    return ret

@register.inclusion_tag('object_list_carts.html', takes_context=True)
def object_list_carts(context, queryset):
    """ Carts to appear as "actions" at the bottom of some objects list
    """
    ret = {}
    try:
        if queryset is not None and hasattr(queryset, 'model'):
            ret['carts'] = map(cart2dict, context['carts'].carts_for_model(queryset.model))
            ret['has_cart'] = bool(ret['carts'])
    except Exception:
        logger.warning("Cannot resolve session carts:", exc_info=True)
        if settings.DEBUG:
            raise
    return ret

@register.simple_tag(takes_context=True)
def do_action(context):
    ret = ''
    try:
        ret = context['action_fn'](context) or ''
        context['action_done'] = True
    except Exception:
        logger.warning("Cannot do action:", exc_info=True)
        if settings.DEBUG:
            raise
    return ret


# Post-login: retrieve the session carts...