# -*- encoding: utf-8 -*-
from collections import defaultdict
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from common.models import Supplier, Location
from assets.models import Item, ItemTemplate, ItemGroup
from company.models import Department

from common.api import role_from_request
from dynamic_search.api import register
import datetime
import logging
from settings import DATE_FMT_FORMAT

logger = logging.getLogger(__name__)

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

class PurchaseOrderManager(models.Manager):
    def by_request(self, request):
        Q = models.Q
        try:
            if request.user.is_superuser:
                return self.all()
            else:
                active_role = role_from_request(request)
                if active_role:
                    # remember: location_src is always the supplier!
                    q = Q(movements__location_dest__department=active_role.department) \
                        | Q(department=active_role.department)
                else:
                    q = Q(create_user=request.user) | Q(validate_user=request.user) \
                        | Q(department__in=request.user.dept_roles.values_list('department', flat=True))
                return self.filter(q)
        except Exception:
            logger.exception("cannot filter:")
        return self.none()

class PurchaseOrder(models.Model):
    objects = PurchaseOrderManager()
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
    department = models.ForeignKey(Department, verbose_name=_("corresponding department"), 
                blank=True, null=True, related_name='+')

    class Meta:
        verbose_name = _(u'purchase order')
        verbose_name_plural = _(u'purchase orders')
        permissions = ( ('receive_purchaseorder', 'Can receive a purchase order'),
                ('validate_purchaseorder', 'Can validate a purchase order'), )

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
        logger = logging.getLogger('apps.movements.PurchaseOrder.calc')

        # 1st step: fill dicts with the things we've ordered
        for item in self.items.all():
            if not item.received_qty:
                continue

            if not item.item_template_id:
                raise ValueError(_('Item template for item "%s" has not been assigned. Cannot continue.'), item.item_name)
            serials = []

            if item.item_template.category.is_group:
                # Skip group containers. We never receive them as items
                continue
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
                biid = bid.item_template_id
                po_bundled_qty[biid] = po_bundled_qty.get(biid, 0) + item.received_qty

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
                new_move.items.create(item_template_id=iid, is_bundled=True)
        return True

    def recalc_bundle_items(self):
        """Restore the relation of bundled items to their parents of a PO
        """
        logger = logging.getLogger('apps.movements.PurchaseOrder.calc')
        lbdls = Location.objects.filter(department__isnull=True, usage='production')[:1]
        if not lbdls:
            raise RuntimeError(_(u'This is no bundling location configured in the system!'))
        pending_bundled = defaultdict(list)

        for mm in self.movements.filter(location_dest=lbdls[0]):
            for bb in mm.items.filter(bundled_in__isnull=True):
                pending_bundled[bb.item_template_id].append(bb)

        logger.debug("Pending bundled: %d items of %d products", sum(map(len, pending_bundled.values())), len(pending_bundled))
        for item in self.items.all():
            if not item.received_qty:
                continue

            if (not item.item_template_id) or item.item_template.category.is_group:
                # Skip non-ready lines or group containers.
                continue
            if not (item.item_template.category.is_bundle and item.bundled_items.exists()):
                continue

            serials = []
            for s in item.serial_nos.split(','):
                s = s.strip()
                if s:
                    serials.append(s)

            rqty = item.received_qty - len(serials)
            assert rqty >= 0, "serials more than received for line %d %s" %(item.id, item)
            serials = set(serials)

            for bitem in Item.objects.filter(movements__purchase_order=self, item_template=item.item_template).iterator():
                if bitem.serial_number:
                    if bitem.serial_number not in serials:
                        continue
                    serials.remove(bitem.serial_number)
                else:
                    if rqty < 1:
                        continue
                    rqty -= 1
                igroup, c = ItemGroup.objects.get_or_create(item_ptr=bitem,
                                defaults={'item_template': bitem.item_template })
                bitem.save() # just restore the other fields
                if c:
                    logger.debug("Created itemgroup for item %d, to host bundled items", bitem.id)
                logger.debug("Arrived at bundle #%d %s for line #%d %s: group %d",
                            bitem.id, bitem, item.id, item, igroup.id)

                # count the items already bundled, by template id
                acc_bundled = defaultdict(int)
                for ab in igroup.items.all():
                    acc_bundled[ab.item_template_id] += ab.qty
                # we now *repeat* this for every serial/single item created for this
                # PO line:

                for buli in item.bundled_items.all():
                    missing = buli.qty - acc_bundled[buli.item_template_id]
                    if missing < 0: # can happen if we have 2x buli lines for the same template
                        acc_bundled[buli.item_template_id] -= buli.qty
                        continue
                    elif missing > 0:
                        logger.debug("Need to bundle %d more '%s' in '%s'",
                                    missing, buli.item_template, bitem)
                        ub = []
                        while missing and len(pending_bundled[buli.item_template_id]):
                            unbundled = pending_bundled[buli.item_template_id].pop(0)
                            if unbundled.qty > missing:
                                # Rare case, not currently possible: there is an item
                                # whose quantity is more than we want to connect here
                                ub.append(unbundled)
                                continue

                            unbundled.bundled_in = [igroup, ] # add to our group
                            missing -= unbundled.qty
                            unbundled.save()

                        if ub:
                            pending_bundled[buli.item_template_id] += ub

                        if missing:
                            logger.debug("Still missing %d items of '%s' for '%s'",
                                    missing, buli.item_template, bitem)
            if rqty or len(serials):
                logger.info("Remaining %d items to process for line %s", rqty + len(serials), item)

        # end of fn

    def get_cart_name(self):
        """ Returns the "shopping-cart" name of this model
        """
        return _("Purchase Order: %s") % self.name

    def get_cart_itemcount(self):
        """ Returns the number of items currently at the cart
        """
        return self.items.count()

    @models.permalink
    def get_cart_url(self):
        # TODO
        return ('purchase_order_view', [str(self.id)])

    def get_cart_objcap(self, obj):
        """ Return the state of `obj` in our cart, + the action url
        """
        if obj is None or not isinstance(obj, ItemTemplate):
            # "incorrect object passed:", repr(obj)
            return None, None

        # We treat all products as not-added and allow duplicates
        #if self.items.filter(id=obj.id).exists():
            #state = 'added'
            #view_name = 'purchaseorder_item_remove'
        #else:
        if True:
            state = 'removed'
            view_name = 'purchaseorder_item_add'

        # prepare the url (TODO cache)
        href = reverse(view_name, args=(str(self.id),))
        return state, href

    def add_to_cart(self, obj):
        if obj is None or not isinstance(obj, ItemTemplate):
            raise TypeError(_("Incorrect object passed: %s") % repr(obj))

        self.items.create(item_template=obj, received_qty=1)
        return 'added'

    def remove_from_cart(self, obj):
        # FIXME: we may want to disable this function entirely
        if obj is None or not isinstance(obj, ItemTemplate):
            raise TypeError(_("Incorrect object passed: %s") % repr(obj))

        done = False
        for item in self.items.filter(item_template=obj.id):
            item.delete()
            done = True
            break
        if not done:
            raise ValueError(_("Product %s not in movement!") % unicode(obj))
        self.save()
        return 'removed'

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
    in_group = models.IntegerField(verbose_name=_("In group"), null=True, blank=True)

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

    def get_cart_name(self):
        """ Returns the "shopping-cart" name of this model
        """
        if self.item_template:
            main = unicode(self.item_template)
        else:
            main = self.item_name
        return _("PO Item: %s") % main

    def get_cart_itemcount(self):
        """ Returns the number of items currently at the cart
        """
        return self.bundled_items.count()

    @models.permalink
    def get_cart_url(self):
        # TODO
        return ('purchase_order_update', [str(self.purchase_order.id)])

    def get_cart_objcap(self, obj):
        """ Return the state of `obj` in our cart, + the action url
        """
        if obj is None or not isinstance(obj, ItemTemplate):
            # "incorrect object passed:", repr(obj)
            return None, None

        #if self.item_template and self.item_template == obj:
        #    state = 'added'
        #    view_name = 'purchaseorder_item_remove'
        #if self.items.filter(id=obj.id).exists():
            #state = 'added'
            #view_name = 'purchaseorder_item_remove'
        #else:
        if not self.item_template:
            state = 'removed'
            view_name = 'purchaseorder_item_product_add'
        elif self.item_template.category.is_bundle:
            state = 'removed'
            view_name = 'purchaseorder_item_bundled_add'
        else:
            return None, None

        href = reverse(view_name, args=(str(self.id),))
        return state, href

    def add_to_cart(self, obj):
        """ This will add the product to the *bundled* items
        """
        if obj is None or not isinstance(obj, ItemTemplate):
            raise TypeError(_("Incorrect object passed: %s") % repr(obj))

        self.bundled_items.add(obj)
        return 'added'

    def remove_from_cart(self, obj):
        # FIXME: we may want to disable this function entirely
        if obj is None or not isinstance(obj, ItemTemplate):
            raise TypeError(_("Incorrect object passed: %s") % repr(obj))

        done = False
        if self.item_template and obj == self.item_template:
            self.item_template = None
            done = True
        else:
            for item in self.bundled_items.filter(pk=obj.id):
                item.delete()
                done = True
                break
        if not done:
            raise ValueError(_("Product %s not in line!") % unicode(obj))
        self.save()
        return 'removed'

    def set_main_product(self, obj):
        """ This will set the product as the item_template
        """
        if obj is None or not isinstance(obj, ItemTemplate):
            raise TypeError(_("Incorrect object passed: %s") % repr(obj))

        self.item_template = obj
        self.save()
        return 'return'

class PurchaseOrderBundledItem(models.Model):
    parent_item = models.ForeignKey(PurchaseOrderItem, verbose_name=_("bundled items"), related_name="bundled_items")
    item_template = models.ForeignKey(ItemTemplate, verbose_name=_(u'item template'), null=True, blank=True)
    qty = models.PositiveIntegerField(default=1, verbose_name=_(u'quantity'))

    class Meta:
        verbose_name = _(u'bundled item')
        verbose_name_plural = _(u'bundled items')

    def __unicode__(self):
        return unicode(self.item_template)

class MovementManager(models.Manager):
    def by_request(self, request):
        Q = models.Q
        try:
            if request.user.is_superuser:
                return self.all()
            else:
                active_role = role_from_request(request)
                if active_role:
                    q = Q(location_src__department=active_role.department) \
                          | Q(location_dest__department=active_role.department)
                else:
                    allowed_depts = request.user.dept_roles.values_list('department', flat=True)
                    q = Q(create_user=request.user) | Q(validate_user=request.user) \
                        | Q(location_src__department__in=allowed_depts) \
                        | Q(location_dest__department__in=allowed_depts)
                return self.filter(q)
        except Exception:
            logger.exception("cannot filter:")
        return self.none()

class Movement(models.Model):
    objects = MovementManager()
    date_act = models.DateField(auto_now_add=False, verbose_name=_(u'date performed'), 
            help_text=_("Format: 23/04/2010"))
    date_val = models.DateField(verbose_name=_(u'date validated'), blank=True, null=True)
    create_user = models.ForeignKey('auth.User', related_name='+', verbose_name=_('created by'))
    validate_user = models.ForeignKey('auth.User', blank=True, null=True, related_name='+', verbose_name=_('validated by'))

    name = models.CharField(max_length=32, blank=True, verbose_name=_(u'reference'))
    state = models.CharField(max_length=16, default='draft', choices=[('draft', _('Draft')), ('pending', _('Pending')), ('done', _('Done'))])
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
        permissions = (('validate_movement', 'Can validate a movement'), )

    def clean(self):
        """Before saving the Movement, update checkpoint_src to the last validated one
        """
        from inventory.models import Inventory
        super(Movement, self).clean()
        locs = []
        if self.location_dest_id and self.location_dest.usage in 'internal':
            locs.append(self.location_dest)
        if self.location_src_id and self.location_src.usage in 'internal':
            locs.append(self.location_src)

        if locs:
            # find if there is any validated inventory for either location,
            # use it as checkpoint_src
            chks = Inventory.objects.filter(location__in=locs, date_val__isnull=False). \
                        order_by('-date_act')[:1]
            if chks:
                self.checkpoint_src = chks[0]

    def do_close(self, val_user, val_date=None):
        """Check the items and set the movement as 'done'

        This function does the most important processing of a movement. It will
        check the integrity of all contained data, and then update the inventories
        accordingly.
        """
        if val_date is None:
            val_date = datetime.date.today()

        if self.state not in ('draft', 'pending'):
            raise ValueError(_("Cannot close movement %(move)s (id: %(mid)s) because it is not in draft state") % dict(move=self.name, mid=self.id))
        if self.validate_user:
            raise ValueError(_("Cannot close movement because it seems already validated!"))

        if self.checkpoint_dest is not None:
            raise ValueError(_("Internal error, movement is already checkpointed"))

        self.clean()
        if self.checkpoint_src and self.date_act <= self.checkpoint_src.date_act:
            raise ValueError(_("You are not allowed to make any movements before %s, when last inventory was validated") %\
                        self.checkpoint_src.date_act.strftime(DATE_FMT_FORMAT))

        if not self.items.exists():
            raise ValueError(_("You cannot close a movement with no items selected"))

        all_items = self.items.all()
        for item in all_items:
            if not item.item_template.approved:
                raise ValueError(_("Product %s is not approved, you cannot use it in this movement") % \
                        item.item_template)
            if item.location_id == self.location_src_id:
                pass
            elif item.location is None and self.location_src.usage in ('procurement', 'supplier'):
                # Bundled items can come from None, end up in 'bundles'
                pass
            else:
                raise ValueError(_("Item %(item)s is at %(location)s, rather than the move source location!") % \
                        dict(item=unicode(item), location=item.location))

        if self.stype == 'in' and self.purchase_order_id and self.purchase_order.procurement_id:
            all_items.update(src_contract=self.purchase_order.procurement)
        # everything seems OK by now...
        all_items.update(location=self.location_dest)
        if self.stype == 'in':
            for item in all_items:
                if not item.property_number:
                    # a plain save will update the property_number
                    item.save()
        self.validate_user = val_user
        self.date_val = val_date
        self.state = 'done'
        self.save()
        return True

    @models.permalink
    def get_absolute_url(self):
        return ('movement_view', [str(self.id)])

    def __unicode__(self):
        try:
            location_src = self.location_src
            location_dest = self.location_dest
        except Exception:
            location_src = '?'
            location_dest = '?'
        return _(u'%(name)s from %(src)s to %(dest)s') % {'name': self.name or self.origin or _('Move'), \
                    'src': location_src, 'dest': location_dest }

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


register(PurchaseRequestStatus, _(u'purchase request status'), ['name'])
register(PurchaseRequest, _(u'purchase request'), ['user_id', 'id', 'budget', 'required_date', 'status__name', 'originator'])
register(PurchaseRequestItem, _(u'purchase request item'), ['item_template__description', 'qty', 'notes'])
register(PurchaseOrderStatus, _(u'purchase order status'), ['name'])
register(PurchaseOrderItemStatus, _(u'purchase order item status'), ['name'])
register(PurchaseOrder, _(u'purchase order'), ['user_id', 'id', 'required_date', 'status__name', 'supplier__name', 'notes'])
register(PurchaseOrderItem, _(u'purchase order item'), ['item_template__description', 'qty'])
