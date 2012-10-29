# -*- encoding: utf-8 -*-
import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
#from django.contrib.auth.models import User, UserManager
#from django.core.urlresolvers import reverse

from dynamic_search.api import register
from common import models as common
from assets import models as assets
from products import models as products

class Log(models.Model):
    timedate = models.DateTimeField(auto_now_add=True, verbose_name=_(u"timedate"))
    action = models.CharField(max_length=32)
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
    create_user = models.ForeignKey('auth.User', related_name='+')
    validate_user = models.ForeignKey('auth.User', blank=True, null=True, related_name='+')


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
        return 42
    
    def get_cart_url(self):
        return self.get_absolute_url()

class InventoryItem(models.Model):
    inventory = models.ForeignKey(Inventory, related_name='items')
    asset = models.ForeignKey(assets.Item)
    quantity = models.IntegerField()
    state = models.ForeignKey(assets.State, verbose_name=_(u"item state"), 
            null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = _(u'inventory item')
        verbose_name_plural = _(u'inventory items')
        ordering = ['id',]

    @models.permalink
    def get_absolute_url(self):
        return ('inventory_item_view', [str(self.id)])

    def __unicode__(self):
        return "%s: '%s' qty=%s @ %s" % (self.inventory, self.asset, self.quantity, self.date)


register(Inventory, _(u'inventory'), ['name', 'location__name'])

#eof
