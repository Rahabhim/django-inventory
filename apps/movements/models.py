# -*- encoding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from common.models import Supplier, Location
from assets.models import Item, ItemTemplate

from dynamic_search.api import register
import datetime
import logging

class PurchaseRequestStatus(models.Model):
    name = models.CharField(verbose_name=_(u'name'), max_length=32)

    class Meta:
        verbose_name = _(u'purchase request status')
        verbose_name_plural = _(u'purchase request status')

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('purchase_request_state_list', [])


class PurchaseRequest(models.Model):
    user_id = models.CharField(max_length=32, null=True, blank=True, verbose_name=_(u'user defined id'))
    issue_date = models.DateField(auto_now_add=True, verbose_name=_(u'issue date'))
    required_date = models.DateField(null=True, blank=True, verbose_name=_(u'date required'))
    budget = models.PositiveIntegerField(null=True, blank=True, verbose_name=_(u'budget'))
    active = models.BooleanField(default=True, verbose_name=_(u'active'))
    status = models.ForeignKey(PurchaseRequestStatus, null=True, blank=True, verbose_name=_(u'status'))
    originator = models.CharField(max_length=64, null=True, blank=True, verbose_name=_(u'originator'))
    notes = models.TextField(null=True, blank=True, verbose_name=_(u'notes'))

    #account number

    class Meta:
        verbose_name = _(u'purchase request')
        verbose_name_plural = _(u'purchase requests')

    def __unicode__(self):
        return '#%s (%s)' % (self.user_id if self.user_id else self.id, self.issue_date)

    @models.permalink
    def get_absolute_url(self):
        return ('purchase_request_view', [str(self.id)])

    def fmt_active(self):
        if self.active:
            return _(u'Open')
        else:
            return _(u'Closed')

class PurchaseRequestItem(models.Model):
    purchase_request = models.ForeignKey(PurchaseRequest, verbose_name=_(u'purchase request'))
    item_template = models.ForeignKey(ItemTemplate, verbose_name=_(u'item template'))
    qty = models.PositiveIntegerField(verbose_name=_(u'quantity'))
    notes = models.TextField(null=True, blank=True, verbose_name=_(u'notes'))

    class Meta:
        verbose_name = _(u'purchase request item')
        verbose_name_plural = _(u'purchase request items')

    def __unicode__(self):
        return unicode(self.item_template)

    @models.permalink
    def get_absolute_url(self):
        return ('purchase_request_view', [str(self.purchase_request_id)])


class PurchaseOrderStatus(models.Model):
    name = models.CharField(verbose_name=_(u'name'), max_length=32)

    class Meta:
        verbose_name = _(u'purchase order status')
        verbose_name_plural = _(u'purchase order status')

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('purchase_order_state_list', [])

class PurchaseOrder(models.Model):
    user_id = models.CharField(max_length=32, null=True, blank=True, verbose_name=_(u'user defined id'))
    purchase_request = models.ForeignKey(PurchaseRequest, null=True, blank=True, verbose_name=_(u'purchase request'))
    procurement = models.ForeignKey('procurements.Contract', null=True, blank=True, verbose_name=_("procurement contract"))
    create_user = models.ForeignKey('auth.User', related_name='+')
    validate_user = models.ForeignKey('auth.User', blank=True, null=True, related_name='+')
    supplier = models.ForeignKey(Supplier, verbose_name=_(u'supplier'))
    issue_date = models.DateField(verbose_name=_(u'issue date'))
    required_date = models.DateField(null=True, blank=True, verbose_name=_(u'date required'))
    active = models.BooleanField(default=True, verbose_name=_(u'active'))
    notes = models.TextField(null=True, blank=True, verbose_name=_(u'notes'))
    status = models.ForeignKey(PurchaseOrderStatus, null=True, blank=True, verbose_name=_(u'status'))

    class Meta:
        verbose_name = _(u'purchase order')
        verbose_name_plural = _(u'purchase orders')

    def __unicode__(self):
        return '#%s (%s)' % (self.user_id if self.user_id else self.id, self.issue_date)

    @models.permalink
    def get_absolute_url(self):
        return ('purchase_order_view', [str(self.id)])

    def fmt_active(self):
        if self.active:
            return _(u'Open')
        else:
            return _(u'Closed')

    def calc_unmoved_items(self):
        """Calculate items mentioned in this PO, prepare for a movement

            @return a dict of item_template.id: (qty, serials) for those left
        """
        po_items = {} # sets of serial numbers
        po_items_qty = {} # counters of quantities
        po_bundled_qty = {} # counters of quantities for bundled items
        logger = logging.getLogger('movements.PurchaseOrder.calc')

        # 1st step: fill dicts with the things we've ordered
        for item in self.items.all():
            if not item.received_qty:
                continue

            if not item.item_template_id:
                raise ValueError(_('Item template for item "%s" has not been assigned. Cannot continue.'), item.item_name)
            serials = []
            for s in item.serial_nos.split(','):
                s = s.strip()
                if s:
                    serials.append(s)
            if item.received_qty < len(serials):
                raise ValueError(_("You have given %(slen)d serials, but marked only %(received)d received items. Please fix either of those") % \
                        dict(slen=len(serials), received=item.received_qty))
            iid = item.item_template_id
            old_serials = po_items.setdefault(iid, set())
            assert not old_serials.intersection(serials), \
                    "Some serials are repeated in po: %s "  % \
                        ','.join(old_serials.intersection(serials))
            old_serials.update(serials)
            po_items_qty[iid] = po_items_qty.get(iid, 0) + item.received_qty - len(serials)
            for bid in item.bundled_items.all():
                po_bundled_qty[bid.id] = po_bundled_qty.get(bid.id, 0) + item.received_qty

        # 2st step: remove from dicts those items who are already in movements
        #           linked to this one
        #for move in self.movements.all(): #.prefetch_related('items'): Django 1.4
        #    for item in move.items.iterator():
        if True:
            for item in Item.objects.filter(movements__purchase_order=self).iterator():
                if item.qty < 1:
                    raise ValueError("Zero or negative quantity found for asset #%d" % item.id)
                iset = po_items.get(item.item_template_id, set())
                iqty = po_items_qty.get(item.item_template_id, 0)
                bqty = po_bundled_qty.get(item.item_template_id, 0)
                
                logger.debug("item %s start: %d, %d, %s", item, iqty, bqty, iset)
                if iset and item.serial_number and item.serial_number in iset:
                    iset.remove(item.serial_number)
                elif iqty:
                    if item.qty > iqty:
                        iqty = 0
                    else:
                        iqty -= item.qty
                    po_items_qty[item.item_template_id] = iqty
                elif bqty:
                    if item.qty > bqty:
                        bqty = 0
                    else:
                        bqty -= item.qty
                    po_bundled_qty[item.item_template_id] = bqty
                else:
                    # Item of movement is not in PO list, iz normal.
                    logger.debug("item %s not in po %d, %d, %s", item, iqty, bqty, iset)
                    continue

        # 3rd step: prepare output dictionary
        out = {}
        for k, v in po_items.items():
            if not v: continue
            out[k] = (0, v)
        for k, v in po_items_qty.items():
            if not v: continue
            if k in out:
                # out[k][0] must be 0, still
                ks = out[k][1]
            else:
                ks = set()
            out[k] = (v, ks)
        
        for k, v in po_bundled_qty.items():
            if not v: continue
            out[(k,1)] = (v, set())
        logger.debug("Have left: %r", out)
        return out

    def fill_out_movement(self, cunmoved, new_move):
        """ fill the supplied movement with [new] items for those of calc_unmoved_items()
        """
        assert cunmoved
        bundled = []
        for iid, two in cunmoved.items():
            qty, serials = two
            if isinstance(iid, tuple):
                assert iid[1] == 1, "Strange index: %r" % iid
                assert not serials, "Serials in bundle? %r" % serials
                bundled.append((iid[0], qty))
                continue
            for s in serials:
                new_item, c = Item.objects.get_or_create(item_template_id=iid, serial_number=s)
                new_move.items.add(new_item) #FIXME
            for i in range(qty):
                # create individual items of item.qty=1
                new_move.items.create(item_template_id=iid)
        return bundled

    def fill_out_bundle_move(self, bundled, new_move):
        """ fill the supplied movement with [new] bundled items, from fill_out_movement()
        """
        assert bundled
        for iid, qty in bundled:
            for i in range(qty):
                # create individual items of item.qty=1
                new_move.items.create(item_template_id=iid)
        return True

class PurchaseOrderItemStatus(models.Model):
    name = models.CharField(verbose_name=_(u'name'), max_length=32)

    class Meta:
        verbose_name = _(u'purchase order item status')
        verbose_name_plural = _(u'purchase order item status')

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('purchase_order_item_state_list', [])


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, verbose_name=_(u'purchase order'), related_name='items')
    item_name = models.CharField(max_length=128, null=True, blank=True,
                verbose_name=_(u"Item description"), ) # help_text=_("Fill this in before the product can be assigned")
    item_template = models.ForeignKey(ItemTemplate, verbose_name=_(u'item template'), null=True, blank=True)
    agreed_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, verbose_name=_(u'agreed price'))
    active = models.BooleanField(default=True, verbose_name=_(u'active'))
    status = models.ForeignKey(PurchaseOrderItemStatus, null=True, blank=True, verbose_name=_(u'status'))
    qty = models.PositiveIntegerField(default=1, verbose_name=_(u'quantity'))
    received_qty = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name=_(u'received'))
    serial_nos = models.CharField(max_length=512, verbose_name=_(u"Serial Numbers"), blank=True)
    bundled_items = models.ManyToManyField(ItemTemplate, verbose_name=_("bundled items"), 
                null=True, blank=True, related_name='+')

    class Meta:
        verbose_name = _(u'purchase order item')
        verbose_name_plural = _(u'purchase order items')

    def __unicode__(self):
        return unicode(self.item_template)

    @models.permalink
    def get_absolute_url(self):
        return ('purchase_order_view', [str(self.purchase_order_id)])

    def fmt_agreed_price(self):
        if self.agreed_price:
            return '€ %s' % self.agreed_price
        else:
            return ''

    def fmt_active(self):
        if self.active:
            return _(u'Open')
        else:
            return _(u'Closed')

class Movement(models.Model):
    date_act = models.DateField(auto_now_add=False, verbose_name=_(u'date performed'))
    date_val = models.DateField(verbose_name=_(u'date validated'), blank=True, null=True)
    create_user = models.ForeignKey('auth.User', related_name='+', verbose_name=_('created by'))
    validate_user = models.ForeignKey('auth.User', blank=True, null=True, related_name='+', verbose_name=_('validated by'))
    
    name = models.CharField(max_length=32, blank=True, verbose_name=_(u'reference'))
    state = models.CharField(max_length=16, default='draft', choices=[('draft', _('Draft')), ('done', _('Done'))])
    stype = models.CharField(max_length=16, choices=[('in', _('Incoming')),('out', _('Outgoing')), 
                ('internal', _('Internal')), ('other', _('Other'))], verbose_name=_('type'))
    origin = models.CharField(max_length=64, blank=True, verbose_name=_('origin'))
    note = models.TextField(verbose_name=_('Notes'), blank=True)
    location_src = models.ForeignKey(Location, related_name='location_src', verbose_name=_("source location"))
    location_dest = models.ForeignKey(Location, related_name='location_dest', verbose_name=_("destination location"))
    items = models.ManyToManyField(Item, verbose_name=_('items'), related_name='movements', blank=True)
    # limit_choices_to these at location_src
    
    checkpoint_src = models.ForeignKey('inventory.Inventory', verbose_name=_('Source checkpoint'),
                null=True, blank=True, related_name='+')
    checkpoint_dest = models.ForeignKey('inventory.Inventory', verbose_name=_('Destination checkpoint'),
                null=True, blank=True, related_name='+')

    purchase_order = models.ForeignKey(PurchaseOrder, blank=True, null=True, related_name='movements')

    class Meta:
        verbose_name = _("movement")
        verbose_name_plural = _("movements")

    def do_close(self, val_user, val_date=None):
        """Check the items and set the movement as 'done'

        This function does the most important processing of a movement. It will
        check the integrity of all contained data, and then update the inventories
        accordingly.
        """
        if val_date is None:
            val_date = datetime.date.today()

        if self.state != 'draft':
            raise ValueError(_("Cannot close movement %(move)s (id: %(mid)s) because it is not in draft state") % dict(move=self.name, mid=self.id))
        if self.validate_user:
            raise ValueError(_("Cannot close movement because it seems already validated!"))

        all_items = self.items.all()
        for item in all_items:
            if item.location_id == self.location_src_id:
                pass
            elif item.location is None and self.location_src.usage in ('procurement', 'supplier'):
                # Bundled items can come from None, end up in 'bundles'
                pass
            else:
                raise ValueError(_("Item %(item)s is at %(location)s, rather than the move source location!") % \
                        dict(item=unicode(item), location=item.location))

        # TODO: validate that all itemgroups of items are active

        # everything seems OK by now...
        all_items.update(location=self.location_dest)
        self.validate_user = val_user
        self.date_val = val_date
        self.state = 'done'
        self.save()
        return True

    @models.permalink
    def get_absolute_url(self):
        return ('movement_view', [str(self.id)])

    def __unicode__(self):
        return _(u'%(name)s from %(src)s to %(dest)s') % {'name': self.name or self.origin or _('Move'), \
                    'src': self.location_src, 'dest': self.location_dest}

    def get_cart_name(self):
        """ Returns the "shopping-cart" name of this model
        """
        # TODO by type
        return _("Movement: %s") % self.name

    def get_cart_itemcount(self):
        """ Returns the number of items currently at the cart
        """
        return self.items.count()

    @models.permalink
    def get_cart_url(self):
        # TODO
        return ('movement_view', [str(self.id)])

    def get_cart_objcap(self, obj):
        """ Return the state of `obj` in our cart, + the action url
        """
        if obj is None or not isinstance(obj, Item):
            # "incorrect object passed:", repr(obj)
            return None, None

        if self.items.filter(id=obj.id).exists():
            state = 'added'
            view_name = 'movement_item_remove'
        else:
            if obj.location == self.location_src:
                state = 'removed'
                view_name = 'movement_item_add'
            else:
                # "wrong location"
                return False, None

        # prepare the url (TODO cache)
        href = reverse(view_name, args=(str(self.id),))
        return state, href

    def add_to_cart(self, obj):
        if obj is None or not isinstance(obj, Item):
            raise TypeError(_("Incorrect object passed: %s") % repr(obj))

        if self.items.filter(id=obj.id).exists():
            raise ValueError(_("Item already in movement"))

        self.items.add(obj)
        return 'added'

    def remove_from_cart(self, obj):
        if obj is None or not isinstance(obj, Item):
            raise TypeError(_("Incorrect object passed: %s") % repr(obj))

        done = False
        for item in self.items.filter(id=obj.id):
            item.delete()
            done = True
        if not done:
            raise ValueError(_("Item %s not in movement!") % unicode(obj))
        self.save()
        return 'removed'

#class MovementLine(models.Model):
    #movement = models.ForeignKey(Movement)
    #asset = models.ForeignKey(Item)

register(PurchaseRequestStatus, _(u'purchase request status'), ['name'])
register(PurchaseRequest, _(u'purchase request'), ['user_id', 'id', 'budget', 'required_date', 'status__name', 'originator'])
register(PurchaseRequestItem, _(u'purchase request item'), ['item_template__description', 'qty', 'notes'])
register(PurchaseOrderStatus, _(u'purchase order status'), ['name'])
register(PurchaseOrderItemStatus, _(u'purchase order item status'), ['name'])
register(PurchaseOrder, _(u'purchase order'), ['user_id', 'id', 'required_date', 'status__name', 'supplier__name', 'notes'])
register(PurchaseOrderItem, _(u'purchase order item'), ['item_template__description', 'qty'])
