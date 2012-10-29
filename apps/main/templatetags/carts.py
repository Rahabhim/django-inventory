# -*- encoding: utf-8 -*-
from django import template
import logging
from main import cart_utils
import settings

register = template.Library()
logger = logging.getLogger('main.carts')

@register.simple_tag(takes_context=True)
def prepare_session_carts(context):
    try:
        session = template.Variable('request').resolve(context).session
        if 'carts' not in session:
            session['carts'] = []
            # session.modified = True
    except Exception:
        logger.warning("Cannot resolve session:", exc_info=True)
        if settings.DEBUG:
            raise
    
    return ''

@register.inclusion_tag('session_carts.html', takes_context=True)
def session_carts(context):
    """Opened carts for a user session

        They should appear at the top of the menu or so.
        Also calls "prepare_session_carts"
    """
    session = None
    prepare_session_carts(context)

    try:
        session = template.Variable('request').resolve(context).session
        return {'carts': cart_utils.get_session_carts(session) }

    except Exception:
        logger.warning("Cannot resolve session carts:", exc_info=True)
        if settings.DEBUG:
            raise

    return {}

@register.inclusion_tag('object_carts.html', takes_context=True)
def object_carts(context, obj):
    """ Carts to appear as "actions" inside some object's line
    """
    pass

@register.inclusion_tag('object_list_carts.html', takes_context=True)
def object_list_carts(context, obj):
    """ Carts to appear as "actions" at the bottom of some objects list
    """
    pass


# Post-login: retrieve the session carts...