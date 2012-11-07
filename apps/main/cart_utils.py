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

    Then, we place a 'carts' attribute in the RequestContext, through the middleware
    function `in_context()` . That attribute will hold Model() objects that represent
    carts.
"""

class CartsContainer(object):
    """Holds list of carts, in an indexed way
    """
    def __init__(self, session_carts):
        self._session_carts = session_carts
        self._carts = {} # holds tuple(<cart_object>, (dest) )

    def __iter__(self):
        for c, dest in self._carts.values():
            yield c

    def load_all(self):
        for scart in self._session_carts:
            try:
                sref = scart['ref']
                cart = models.get_model(sref[0], sref[1]).objects.get(pk=sref[2])
                self._carts[sref] = (cart, scart.get('dest', None))
            except ObjectDoesNotExist:
                logger.debug("Stale cart object in session: %s.%s #%s", *(scart['ref'][0:3]))

    def carts_for_model(self, for_model):
        assert hasattr(for_model, '_meta'), repr(for_model)
        for_dest = (for_model._meta.app_label, for_model._meta.object_name)

        for c, dest in self._carts.values():
            if dest is None or dest == for_dest:
                yield c

    def open_as_cart(self, obj, destination=None):
        """Register object to be used as a cart
        """
        assert isinstance(obj, models.Model), "obj: %s %s" % (type(obj), repr(obj))
        ref = (obj._meta.app_label, obj._meta.object_name, obj.pk)
        for c in self._session_carts:
            # scan and avoid duplicates
            if c.get('ref',None) == ref:
                return False

        if hasattr(destination, '_meta'):
            destination = (destination._meta.app_label, destination._meta.object_name)
        elif isinstance(destination, basestring):
            destination = tuple(destination.split('.', 1))
        self._session_carts.append(dict(ref=ref, dest=destination))
        self._carts[ref] = (obj, destination)
        return True

    def close_cart(self, obj):
        assert isinstance(obj, models.Model), "obj: %s %s" % (type(obj), repr(obj))
        ref = (obj._meta.app_label, obj._meta.object_name, obj.pk)

        modified = False
        to_del = []
        for scart in self._session_carts:
            if scart.get('ref') == ref:
                to_del.append(scart)

        for td in to_del:
            # not optimal, but safe...
            self._session_carts.remove(td)
            modified = True

        self._carts.pop(ref, None)
        return modified

def in_context(request):
    if 'carts' not in request.session:
        request.session['carts'] = [] # these are in non-object form

    return dict(carts=CartsContainer(request.session['carts'])) # but these will receive active objects

#eof
