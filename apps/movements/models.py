# -*- encoding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.models import Supplier, Location
from assets.models import Item, ItemTemplate

from dynamic_search.api import register


"""
TODO: PR Change Order model ?
"""


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
    procurement = models.ForeignKey('procurements.Contract', null=True, blank=True)
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
        
        # 1st step: fill dicts with the things we've ordered
        for item in self.items.all():
            if not item.received_qty:
                continue
            serials = []
            for s in item.serial_nos.split(','):
                s = s.strip()
                if s:
                    serials.append(s)
            if item.received_qty < len(serials):
                raise ValueError(_("You have given %d serials, but marked only %d received items. Please fix either of those") % \
                        (len(serials), item.received_qty))
            iid = item.item_template_id
            old_serials = po_items.setdefault(iid, set())
            assert not old_serials.intersection(serials), \
                    "Some serials are repeated in po: %s "  % \
                        ','.join(old_serials.intersection(serials))
            old_serials.update(serials)
            po_items_qty[iid] = po_items_qty.get(iid, 0) + item.received_qty - len(serials)

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
                
                if iset and item.serial_number and item.serial_number in iset:
                    iset.pop(item.serial_number)
                elif iqty:
                    if item.qty > iqty:
                        iqty = 0
                    else:
                        iqty -= item.qty
                    po_items_qty[item.item_template_id] = iqty
                else:
                    # Item of movement is not in PO list, iz normal.
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
        
        print "Have left:", out
        return out

    def fill_out_movement(self, cunmoved, new_move):
        """ fill the supplied movement with [new] items for those of calc_unmoved_items()
        """
        assert cunmoved
        for iid, two in cunmoved.items():
            qty, serials = two
            for s in serials:
                new_item, c = Item.objects.get_or_create(item_template_id=iid, serial_number=s)
                new_move.items.add(new_item) #FIXME
            for i in range(qty):
                # create individual items of item.qty=1
                new_move.items.create(item_template_id=iid)
        

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
    item_template = models.ForeignKey(ItemTemplate, verbose_name=_(u'item template'))
    status = models.ForeignKey(PurchaseRequestStatus, null=True, blank=True, verbose_name=_(u'status'))
    agreed_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, verbose_name=_(u'agreed price'))
    active = models.BooleanField(default=True, verbose_name=_(u'active'))
    status = models.ForeignKey(PurchaseOrderItemStatus, null=True, blank=True, verbose_name=_(u'status'))
    qty = models.PositiveIntegerField(default=1, verbose_name=_(u'quantity'))
    received_qty = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name=_(u'received'))
    serial_nos = models.CharField(max_length=512, verbose_name=_(u"Serial Numbers"), blank=True)

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
    create_user = models.ForeignKey('auth.User', related_name='+')
    validate_user = models.ForeignKey('auth.User', blank=True, null=True, related_name='+')
    
    name = models.CharField(max_length=32, blank=True, verbose_name=_(u'reference'))
    state = models.CharField(max_length=16, default='draft', choices=[('draft', 'Draft'), ('done', 'Done')])
    stype = models.CharField(max_length=16, choices=[('in', 'Incoming'),('out',' Outgoing'), 
                ('internal', 'Internal'), ('other', 'Other')], verbose_name=_('type'))
    origin = models.CharField(max_length=64, blank=True, verbose_name=_('origin'))
    note = models.TextField(verbose_name=_('Notes'), blank=True)
    location_src = models.ForeignKey(Location, related_name='location_src')
    location_dest = models.ForeignKey(Location, related_name='location_dest')
    items = models.ManyToManyField(Item, verbose_name=_('items'), related_name='movements', blank=True)
    # limit_choices_to these at location_src
    
    checkpoint_src = models.ForeignKey('inventory.Inventory', verbose_name=_('Source checkpoint'),
                null=True, blank=True, related_name='+')
    checkpoint_dest = models.ForeignKey('inventory.Inventory', verbose_name=_('Destination checkpoint'),
                null=True, blank=True, related_name='+')

    purchase_order = models.ForeignKey(PurchaseOrder, blank=True, null=True, related_name='movements')

    def do_close(self, val_user):
        """Check the items and set the movement as 'done'
        
        This function does the most important processing of a movement. It will
        check the integrity of all contained data, and then update the inventories
        accordingly.
        """
        raise NotImplementedError

    @models.permalink
    def get_absolute_url(self):
        return ('movement_view', [str(self.id)])

    def __unicode__(self):
        return _(u'%s from %s to %s') % (self.name or self.origin or _('Move'), \
                    self.location_src, self.location_dest)

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
