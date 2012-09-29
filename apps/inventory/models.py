# -*- encoding: utf-8 -*-
import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User, UserManager
from django.core.urlresolvers import reverse

from photos.models import GenericPhoto

from dynamic_search.api import register
from common import models as common
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
    name = models.CharField(max_length=32, verbose_name=_(u'name'))
    location = models.ForeignKey(common.Location, verbose_name=_(u'location'))

    class Meta:
        verbose_name = _(u'inventory')
        verbose_name_plural = _(u'inventories')

    @models.permalink
    def get_absolute_url(self):
        return ('inventory_view', [str(self.id)])

    def __unicode__(self):
        return self.name


class InventoryCheckPoint(models.Model):
    inventory = models.ForeignKey(Inventory)
    datetime = models.DateTimeField(default=datetime.datetime.now())	
    supplies = models.ManyToManyField(products.ItemTemplate, null=True, blank=True, through='InventoryCPQty')


class InventoryCPQty(models.Model):
    supply = models.ForeignKey(products.ItemTemplate)
    check_point = models.ForeignKey(InventoryCheckPoint)
    quantity = models.IntegerField()


class InventoryTransaction(models.Model):
    inventory = models.ForeignKey(Inventory)
    supply = models.ForeignKey(products.ItemTemplate)
    quantity = models.IntegerField()
    date = models.DateField(default=datetime.date.today(), verbose_name=_(u"date"))
    notes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = _(u'inventory transaction')
        verbose_name_plural = _(u'inventory transactions')
        ordering = ['-date', '-id']

    @models.permalink
    def get_absolute_url(self):
        return ('inventory_transaction_view', [str(self.id)])

    def __unicode__(self):
        return "%s: '%s' qty=%s @ %s" % (self.inventory, self.supply, self.quantity, self.date)



register(Inventory, _(u'inventory'), ['name', 'location__name'])
