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

def get_session_carts(session, init=True):
    """Get the carts of some session
    """
    ret = []
    
    for scart in session['carts']:
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

def open_as_cart(obj, session):
    """Register object to be used as a cart within a session
    """
    assert isinstance(obj, models.Model), "obj: %s %s" % (type(obj), repr(obj))
    ref = (obj._meta.app_label, obj._meta.object_name, obj.pk)
    for c in session['carts']:
        # scan and avoid duplicates
        if c.get('ref',None) == ref:
            break
    else:
        session['carts'].append(dict(ref=ref, dest=None))
    session.modified = True

#eof
