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

    @classmethod
    def _add_cart_to_session(cls, ref, session_carts, destination):
        """Register object to be used as a cart
        """
        for c in session_carts:
            # scan and avoid duplicates
            if c.get('ref',None) == ref:
                return False

        if hasattr(destination, '_meta'):
            destination = (destination._meta.app_label, destination._meta.object_name)
        elif isinstance(destination, basestring):
            destination = tuple(destination.split('.', 1))
        session_carts.append(dict(ref=ref, dest=destination))

    def open_as_cart(self, obj, destination=None):
        assert isinstance(obj, models.Model), "obj: %s %s" % (type(obj), repr(obj))
        ref = (obj._meta.app_label, obj._meta.object_name, obj.pk)
        self._add_cart_to_session(ref, self._session_carts, destination)
        self._carts[ref] = (obj, destination)
        return True

    def close_cart(self, obj):
        assert isinstance(obj, models.Model), "obj: %s %s" % (type(obj), repr(obj))
        ref = (obj._meta.app_label, obj._meta.object_name, obj.pk)
        modified = self._remove_from_session(ref, self._session_carts)
        self._carts.pop(ref, None)
        return modified

    def close_carts_by_model(self, model):
        """Closes all carts whose object is that model

            eg. carts.close_carts_by_model(PurchaseOrder) will close any carts that
                are PurchaseOrder instances

            Note: since `model` is only used in `isinstance()`, it can also be a tuple
            of multiple models.
        """
        to_del = []
        for ref, ctup in self._carts.items():
            if isinstance(ctup[0], model):
                to_del.append(ref)

        modified = False
        for td in to_del:
            if self._remove_from_session(td, self._session_carts):
                modified = True
            self._carts.pop(td, None)

        return modified

    @classmethod
    def _remove_from_session(cls, ref, session_carts):
        to_del = []
        modified = False
        for scart in session_carts:
            if scart.get('ref') == ref:
                to_del.append(scart)

        for td in to_del:
            # not optimal, but safe...
            session_carts.remove(td)
            modified = True
        return modified


def remove_from_session(request, obj):
    assert isinstance(obj, models.Model), "obj: %s %s" % (type(obj), repr(obj))
    ref = (obj._meta.app_label, obj._meta.object_name, obj.pk)
    ret = CartsContainer._remove_from_session(ref, request.session['carts'])
    request.session.modified = True
    return ret

def add_cart_to_session(obj, request, destination=None):
    """Register object to be used as a cart
    """
    assert isinstance(obj, models.Model), "obj: %s %s" % (type(obj), repr(obj))
    ref = (obj._meta.app_label, obj._meta.object_name, obj.pk)
    ret = CartsContainer._add_cart_to_session(ref, request.session['carts'], destination)
    request.session.modified = True
    return ret

def in_context(request):
    if 'carts' not in request.session:
        request.session['carts'] = [] # these are in non-object form

    return dict(carts=CartsContainer(request.session['carts'])) # but these will receive active objects

#eof
