# -*- encoding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _
# from django.contrib.contenttypes.models import ContentType

from dynamic_search.api import register
from common.models import Location, Partner, Supplier
from products.models import ItemTemplate, AbstractAttribute

class State(models.Model):
    name = models.CharField(max_length=32, verbose_name=_(u'name'))
    exclusive = models.BooleanField(default=False, verbose_name=_(u'exclusive'))

    class Meta:
        verbose_name = _(u"state")
        verbose_name_plural = _(u"states")

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.exclusive and _(u'exclusive') or _(u'inclusive'))

    @models.permalink
    def get_absolute_url(self):
        return ('state_list', [])


class ItemStateManager(models.Manager):
    def states_for_item(self, item):
        return self.filter(item=item)


class ItemState(models.Model):
    item = models.ForeignKey('Item', verbose_name=_(u"item"))
    state = models.ForeignKey(State, verbose_name=_(u"state"))
    date = models.DateField(verbose_name=_(u"date"), auto_now_add=True)

    objects = ItemStateManager()

    class Meta:
        verbose_name = _(u"item state")
        verbose_name_plural = _(u"item states")

    def __unicode__(self):
        return _(u"%(asset)s, %(state)s since %(date)s") % {'asset':self.item, 'state':self.state.name, 'date':self.date}

    @models.permalink
    def get_absolute_url(self):
        return ('state_update', [str(self.id)])

class Item(models.Model):
    item_template = models.ForeignKey(ItemTemplate, verbose_name=_(u"item template"))
    property_number = models.CharField(verbose_name=_(u"asset number"), max_length=48)
    notes = models.TextField(verbose_name=_(u"notes"), null=True, blank=True)
    serial_number = models.CharField(verbose_name=_(u"serial number"), max_length=48, null=True, blank=True)
    location = models.ForeignKey(Location, verbose_name=_(u"current location"), null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['property_number']
        verbose_name = _(u"asset")
        verbose_name_plural = _(u"assets")

    @models.permalink
    def get_absolute_url(self):
        return ('item_view', [str(self.id)])

    def __unicode__(self):
        states = ', '.join([itemstate.state.name for itemstate in ItemState.objects.states_for_item(self)])

        return "#%s, '%s' %s" % (self.property_number, self.item_template.description, states and "(%s)" % states)

    def states(self):
        return [State.objects.get(pk=id) for id in self.itemstate_set.all().values_list('state', flat=True)]


class ItemGroup(Item):
    """ A group (or bundle) is itself an item, behaves like one in the long run
    
        But the contained items must have their location set to empty.
    """
    items = models.ManyToManyField(Item, blank=True, null=True, verbose_name=_(u"item"), 
            related_name='items+')

    class Meta:
        # ordering = ['name']
        verbose_name = _(u"item group")
        verbose_name_plural = _(u"item groups")

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('group_view', [str(self.id)])




register(ItemState, _(u'states'), ['state__name'])
register(Item, _(u'assets'), ['property_number', 'notes', 'serial_number', ])
register(ItemGroup, _(u'asset groups'), ['name'])

#eof
