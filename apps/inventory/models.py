# -*- encoding: utf-8 -*-

from django.db import models
from django.db.models import Q #, Count
from django.utils import formats
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
#from django.contrib.auth.models import User, UserManager
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError, PermissionDenied
from settings import DATE_FMT_FORMAT

from dynamic_search.api import register
from common import models as common
from common.api import role_from_request
from assets import models as assets

# from products import models as products
from movements import models as movements
import logging
import datetime

logger = logging.getLogger(__name__)

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

class InventoryManager(models.Manager):
    def by_request(self, request):
        try:
            if request.user.is_superuser:
                return self.all()
            else:
                q = Q(create_user=request.user) | Q(validate_user=request.user)
                if request.session.get('current_user_role', False):
                    role_id = request.session['current_user_role']
                    role = request.user.dept_roles.get(pk=role_id)
                    q = q | Q(location__department=role.department)
                return self.filter(q)
        except Exception:
            logger.exception("cannot filter:")
        return self.none()

class Inventory(models.Model):
    """ An inventory is a periodical check of all items at some locations
    """
    objects = InventoryManager()
    name = models.CharField(max_length=32, verbose_name=_(u'inventory number'), blank=True, null=True)
    location = models.ForeignKey(common.Location, verbose_name=_(u'location'), on_delete=models.PROTECT)
    date_act = models.DateField(auto_now_add=False, verbose_name=_(u'date performed'), default=datetime.date.today)
    date_val = models.DateField(verbose_name=_(u'date validated'), blank=True, null=True)
    state = models.CharField(max_length=16, default='draft',
                            choices=[('draft', _('Draft')),
                                    ('pending', _('Pending')),
                                    ('done', _('Done')),
                                    ('reject', _('Rejected'))])
    create_user = models.ForeignKey('auth.User', related_name='+', verbose_name=_("created by"), on_delete=models.PROTECT)
    validate_user = models.ForeignKey('auth.User', blank=True, null=True, related_name='+', verbose_name=_("validated by"), on_delete=models.PROTECT)
    signed_file = models.FileField(verbose_name=_("Signed file"), upload_to='inventories',
                blank=True, null=True)

    class Meta:
        verbose_name = _(u'inventory')
        verbose_name_plural = _(u'inventories')
        permissions = ( ('validate_inventory', 'Can validate an inventory'), )

    @models.permalink
    def get_absolute_url(self):
        return ('inventory_view', [str(self.id)])

    @classmethod
    def can_use(cls, obj, context):
        """Condition function to indicate if an inventory is usable in this context

            Checks that the inventory is open and "belongs" to the user
        """
        assert isinstance(obj, cls), repr(obj)
        if obj.state in ('done', 'reject'):
            return False

        user = context.get('user', None)
        if user is None:
            return False
        if user.is_superuser or user.is_staff or user == obj.create_user:
            return True

        active_role = role_from_request(context['request'])
        if active_role and obj.location.department == active_role.department:
            return True

        return False

    def __unicode__(self):
        date_fmt = formats.get_format('DATE_INPUT_FORMATS')[0]
        if self.name:
            return _("%(name)s on %(date)s") % {'name': self.name, 'date': self.date_act.strftime(date_fmt)}
        else:
            return self.date_act.strftime(date_fmt)

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
        if self.validate_user is not None or self.date_val is not None:
            raise PermissionDenied(_("Inventory is validated, cannot modify"))

        if obj is None or not isinstance(obj, assets.Item):
            raise TypeError(_("Incorrect object passed: %s") % repr(obj))

        if self.items.filter(asset__id=obj.id).exists():
            raise ValueError(_("Item already in inventory"))

        self.items.create(asset=obj, quantity=1)
        return 'added'

    def remove_from_cart(self, obj):
        if self.validate_user is not None or self.date_val is not None:
            raise PermissionDenied(_("Inventory is validated, cannot modify"))

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

    def _compute_state(self, pending_only=True, offset=0, limit=100):
        items_in_inventory = [ ii.asset_id for ii in self.items.all()]
        res = []
        items_base = assets.Item.objects.filter(Q(pk__in=items_in_inventory)|Q(location=self.location)).order_by('id')

        items_in_inventory = set(items_in_inventory)
        have_pending = False
        found = True
        while found and len(res) < limit:
            found = False
            for item in items_base[offset:offset+max(limit, 100)]:
                # max(..,100) is used to prevent small,inefficient batches
                found = True
                if item.id not in items_in_inventory:
                    res.append((item, 'new'))
                    have_pending = True
                elif item.location_id != self.location_id:
                    res.append((item, 'missing'))
                    have_pending = True
                elif not pending_only:
                    res.append((item, 'ok'))
            offset += limit

        if not (have_pending or pending_only):
            # We must search the full set about wrong items, just to raise
            # the correct flag (in case we have `limit` results of 'ok' state)
            items_mismatch = assets.Item.objects.filter( \
                    (Q(pk__in=items_in_inventory) & ~Q(location=self.location)) | \
                    (Q(location=self.location) & ~Q(pk__in=items_in_inventory)) ).exists()

            if items_mismatch:
                have_pending = True
        return (have_pending, res)

    def do_close(self, val_user, val_date=None):
        """Validate the inventory and fix Item quantities

            After a validation, no more Movements will be allowed for the
            inventory's location on an earlier date. All subsequent moves
            will have to use this inventory as checkpoint_src
        """
        Q = models.Q
        # First, check that we are not already closed
        logger.debug("Inventory %d %s do_close()", self.id, self.name)
        if self.state not in ('draft', 'pending'):
            raise ValidationError(_("Cannot validate this inventory, it is: %s") % self.get_state_display() )
        if self.date_val or self.validate_user:
            raise ValidationError(_("Inventory already validated"))

        # Second, check that items match
        # Does an *empty* inventory make sense?
        have_pending, res = self._compute_state(pending_only=True, limit=10)
        if have_pending:
            raise ValidationError(_("Inventory has pending items that don't match computed state. Cannot close"))

        self.date_val = val_date or datetime.date.today()
        if self.date_val < self.date_act:
            raise ValidationError(_("The active date cannot be after the validation date"))

        # Third, check that no movements are later than this inventory
        if movements.Movement.objects.filter(Q(location_src=self.location)|Q(location_dest=self.location))\
                .filter(date_act__gt=self.date_act, state__in=('pending', 'done')).exists():
            raise ValidationError(_("You cannot validate an inventory for %s, because there is movements to/from that location on a later date") %\
                    self.date_act.strftime(DATE_FMT_FORMAT))

        # Mark the inventory as closed
        self.state = 'done'
        self.validate_user = val_user
        self.save()

        # Lock any Done moves that reference our location
        movements.Movement.objects.filter(Q(location_src=self.location)|Q(location_dest=self.location))\
                .filter(checkpoint_dest__isnull=True, state='done', )\
                .update(checkpoint_dest=self)
        logger.info("Inventory %d %s validated and closed", self.id, self.name)

    def do_reject(self, user=None):
        if self.state not in ('draft', 'pending'):
            raise ValidationError(_(u'This inventory is %s, cannot reject.') % self.get_state_display())
        self.state = 'reject'
        self.validate_user = user
        self.save()

class InventoryItem(models.Model):
    inventory = models.ForeignKey(Inventory, related_name='items')
    asset = models.ForeignKey(assets.Item, verbose_name=_("asset"), related_name="inventories")
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
