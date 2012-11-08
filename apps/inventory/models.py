# -*- encoding: utf-8 -*-
import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
#from django.contrib.auth.models import User, UserManager
from django.core.urlresolvers import reverse

from dynamic_search.api import register
from common import models as common
from assets import models as assets
from products import models as products

class Log(models.Model):
    timedate = models.DateTimeField(auto_now_add=True, verbose_name=_(u"timedate"))
    action = models.CharField(max_length=32, verbose_name=_("action"))
    description = models.TextField(verbose_name=_(u"description"), null=True, blank=True)
    #user = models.ForeignKey(User, unique=True)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()

    def __unicode__(self):
#		return "%Y-%m-%d %H:%M:%S" % (self.timedate) #& user  && item
        return "%s, %s - %s" % (self.timedate, self.action, self.content_object)

    @models.permalink
    def get_absolute_url(self):
        return ('log_view', [str(self.id)])


class Inventory(models.Model):
    """ An inventory is a periodical check of all items at some locations
    """
    name = models.CharField(max_length=32, verbose_name=_(u'name'))
    location = models.ForeignKey(common.Location, verbose_name=_(u'location'))
    date_act = models.DateField(auto_now_add=False, verbose_name=_(u'date performed'))
    date_val = models.DateField(verbose_name=_(u'date validated'), blank=True, null=True)
    create_user = models.ForeignKey('auth.User', related_name='+', verbose_name=_("created by"))
    validate_user = models.ForeignKey('auth.User', blank=True, null=True, related_name='+', verbose_name=_("validated by"))


    class Meta:
        verbose_name = _(u'inventory')
        verbose_name_plural = _(u'inventories')

    @models.permalink
    def get_absolute_url(self):
        return ('inventory_view', [str(self.id)])

    def __unicode__(self):
        return self.name

    def get_cart_name(self):
        """ Returns the "shopping-cart" name of this model
        """
        return _("Inventory: %s") % self.name

    def get_cart_itemcount(self):
        """ Returns the number of items currently at the cart
        """
        return self.items.count()

    @models.permalink
    def get_cart_url(self):
        return ('inventory_view', [str(self.id)])

    def get_cart_objcap(self, obj):
        """ Return the state of `obj` in our cart, + the action url
        """
        if obj is None or not isinstance(obj, assets.Item):
            # "incorrect object passed:", repr(obj)
            return None, None

        if self.items.filter(asset__id=obj.id).exists():
            state = 'added'
            view_name = 'inventory_item_remove'
        else:
            if obj.location == self.location:
                state = 'removed'
                view_name = 'inventory_item_add'
            else:
                # "wrong location"
                return False, None

        # prepare the url (TODO cache)
        href = reverse(view_name, args=(str(self.id),))
        return state, href

    def add_to_cart(self, obj):
        if obj is None or not isinstance(obj, assets.Item):
            raise TypeError(_("Incorrect object passed: %s") % repr(obj))

        if self.items.filter(asset__id=obj.id).exists():
            raise ValueError(_("Item already in inventory"))

        self.items.create(asset=obj, quantity=1)
        return 'added'

    def remove_from_cart(self, obj):
        if obj is None or not isinstance(obj, assets.Item):
            raise TypeError(_("Incorrect object passed: %s") % repr(obj))

        done = False
        for item in self.items.filter(asset__id=obj.id):
            item.delete()
            done = True
        if not done:
            raise ValueError(_("Item %s not in inventory!") % unicode(obj))
        self.save()
        return 'removed'

class InventoryItem(models.Model):
    inventory = models.ForeignKey(Inventory, related_name='items')
    asset = models.ForeignKey(assets.Item, verbose_name=_("asset"))
    quantity = models.IntegerField(verbose_name=_("quantity"))
    state = models.ForeignKey(assets.State, verbose_name=_(u"item state"), 
            null=True, blank=True)
    notes = models.TextField(null=True, blank=True, verbose_name=_("notes"))

    class Meta:
        verbose_name = _(u'inventory item')
        verbose_name_plural = _(u'inventory items')
        ordering = ['id',]

    @models.permalink
    def get_absolute_url(self):
        return ('inventory_item_view', [str(self.id)])

    def __unicode__(self):
        return u"%s: '%s' qty=%s" % (unicode(self.inventory), unicode(self.asset), self.quantity)


register(Inventory, _(u'inventory'), ['name', 'location__name'])

#eof
