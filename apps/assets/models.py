# -*- encoding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _
# from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from dynamic_search.api import register
from common.models import Location, Partner, Supplier
from products.models import ItemTemplate, AbstractAttribute
import logging

logger = logging.getLogger(__name__)

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

class ItemManager(models.Manager):
    def by_request(self, request):
        try:
            if request.user.is_superuser:
                return self.all()
            profile = request.user.get_profile()
            if profile.department:
                return self.filter(location__department=profile.department)
                        #| models.Q(location__isnull=True))
        except Exception:
            logger.exception("cannot filter:")
        return self.none()

class Item(models.Model):
    objects = ItemManager()
    item_template = models.ForeignKey(ItemTemplate, verbose_name=_(u"item template"), related_name="item")
    property_number = models.CharField(verbose_name=_(u"asset number"), max_length=48)
    notes = models.TextField(verbose_name=_(u"notes"), null=True, blank=True)
    serial_number = models.CharField(verbose_name=_(u"serial number"), max_length=64, null=True, blank=True)
    location = models.ForeignKey(Location, verbose_name=_(u"current location"), null=True, blank=True)
    active = models.BooleanField(default=True, verbose_name=_("active"))
    qty = models.PositiveIntegerField(default=1, verbose_name=_('quantity'),
            help_text=_("Allows a batch of identical items to be referenced as one entity") )
    is_bundled = models.BooleanField(default=False,
            help_text=_("If true, this item is bundled in a group, and therefore has no location"))

    # δυναμικό πεδίο: attributes και τύπος
    class Meta:
        ordering = ['property_number']
        verbose_name = _(u"asset")
        verbose_name_plural = _(u"assets")

    @models.permalink
    def get_absolute_url(self):
        return ('item_view', [str(self.id)])

    @models.permalink
    def get_details_url(self):
        try:
            return ('group_view', [str(self.itemgroup.id)])
        except self.DoesNotExist:
            return ('item_view', [str(self.id)])

    def __unicode__(self):
        states = ', '.join([itemstate.state.name for itemstate in ItemState.objects.states_for_item(self)])

        if self.property_number:
            return "#%s, %s %s" % (self.property_number, self.item_template.description, states and "(%s)" % states)
        else:
            return "%s %s" % (self.item_template.description, states and "(%s)" % states)

    def states(self):
        return [State.objects.get(pk=id) for id in self.itemstate_set.all().values_list('state', flat=True)]

    def clean(self):
        if self.is_bundled and self.location and self.location.usage != 'production':
            raise ValidationError("A bundled item cannot be assigned to any location itself")
        return super(Item, self).clean()

    def get_specs(self):
        return ""
        #if not self.active:
        #    return "spec1"
        #else:
        #    return "spec2"

    def current_location(self):
        if self.location:
            if self.location.usage == 'production':
                if self.itemgroup:
                    return self.itemgroup.current_location()
                return None
            else:
                return self.location

    def get_manufacturer(self):
        return self.item_template.manufacturer.name

    def get_category(self):
        return unicode(self.item_template.category)

class ItemGroup(Item):
    """ A group (or bundle) is itself an item, behaves like one in the long run
    
        But the contained items must have their location set to empty.
    """
    objects = ItemManager()
    items = models.ManyToManyField(Item, blank=True, null=True, verbose_name=_(u"item"), 
            related_name='items+')

    class Meta:
        # ordering = ['name']
        verbose_name = _(u"item group")
        verbose_name_plural = _(u"item groups")

    @models.permalink
    def get_absolute_url(self):
        return ('group_view', [str(self.id)])


register(ItemState, _(u'states'), ['state__name'])
register(Item, _(u'assets'), ['property_number', 'notes', 'serial_number', ])
register(ItemGroup, _(u'item groups'), ['name'])

#eof
