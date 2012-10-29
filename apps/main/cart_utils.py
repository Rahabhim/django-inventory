# -*- encoding: utf-8 -*-
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
import logging

logger = logging.getLogger('main.carts')
"""

    We store scalar information about open "Carts" in the session.
    
    This has the following format
        session['carts'] = list( dict(ref=(app, model, pk), dest=(dapp, dmodel), ),
                    dict(<cart2>), ...)
            
        where:
            app is the application of the Cart object
            model is the model name of the Cart object
            pk the primary key of the opened Cart
        
            dapp, dmodel: application + model of the object this cart shall be filled with

"""

def get_session_carts(session, init=True, for_model=None):
    """Get the carts of some session
    """
    ret = []
    
    for_dest =None
    if for_model is not None:
        assert issubclass(for_model, models.Model), for_model
        for_dest = (for_model._meta.app_label, for_model._meta.object_name)

    for scart in session['carts']:
        if for_dest is not None and scart.get('dest', None) is not None \
                and scart['dest'] != for_dest:
            continue
        try:
            cart = models.get_model(scart['ref'][0], scart['ref'][1]).objects.get(pk=scart['ref'][2])
        except ObjectDoesNotExist:
            logger.debug("Stale cart object in session: %s.%s #%s", *(scart['ref'][0:3]))
            continue
        c = dict(title=cart.get_cart_name(), qty=cart.get_cart_itemcount(), \
                href=cart.get_cart_url())
        ret.append(c)
    
    print "cart ret:", ret
    return ret

def open_as_cart(obj, session, destination=None):
    """Register object to be used as a cart within a session
    """
    assert isinstance(obj, models.Model), "obj: %s %s" % (type(obj), repr(obj))
    ref = (obj._meta.app_label, obj._meta.object_name, obj.pk)
    for c in session['carts']:
        # scan and avoid duplicates
        if c.get('ref',None) == ref:
            break
    else:
        if hasattr(destination, '_meta'):
            destination = (destination._meta.app_label, destination._meta.object_name)
        elif isinstance(destination, basestring):
            destination = tuple(destination.split('.', 1))
        session['carts'].append(dict(ref=ref, dest=destination))
    session.modified = True

def close_cart(obj, session, destination=None):
    assert isinstance(obj, models.Model), "obj: %s %s" % (type(obj), repr(obj))
    ref = (obj._meta.app_label, obj._meta.object_name, obj.pk)
    new_carts = filter(lambda c: c.get('ref',None) != ref, session['carts'])
    if len(new_carts) < len(session['carts']):
        session['carts'] = new_carts
        session.modified = True

def needed_in_cart(obj, session):
    """See if object can be added to any of session's carts
    """
    fdest = (obj._meta.app_label, obj._meta.object_name)
    for cart in session.get('carts', []):
        cdest = cart.get('dest', None)
        if cdest == fdest or cdest is None:
            return True
    return False

#eof
