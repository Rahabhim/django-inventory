# -*- encoding: utf-8 -*-
from collections import defaultdict
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.contrib import messages

from common.models import Supplier, Location, LocationTemplate
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

class _map_item(object):
    """A data object holding a line from PO.map_items()
    """
    def __init__(self, id, parent_id=None, serial=None, item_id=None):
        self.id = id
        self.parent_id = parent_id
        self.serial = serial
        self.item_id = item_id

    def __repr__(self):
        ret =  '<%s ' % (self.id,)
        if self.parent_id:
            ret += ' in %s' % (self.parent_id,)
        if self.serial:
            ret += ' serial=%r' % (self.serial,)
        if self.item_id:
            ret += ' mapped to %r' % (self.item_id,)
        ret += '>'
        return ret

class PurchaseOrder(models.Model):
    objects = PurchaseOrderManager()
    user_id = models.CharField(max_length=32, null=True, blank=True, verbose_name=_(u'user defined id'))
    purchase_request = models.ForeignKey(PurchaseRequest, null=True, blank=True, verbose_name=_(u'purchase request'), on_delete=models.PROTECT)
    procurement = models.ForeignKey('procurements.Contract', null=True, blank=True, verbose_name=_("procurement contract"), on_delete=models.PROTECT)
    create_user = models.ForeignKey('auth.User', related_name='+', verbose_name=_("created by"), on_delete=models.PROTECT)
    validate_user = models.ForeignKey('auth.User', blank=True, null=True, related_name='+', verbose_name=_("validated by"), on_delete=models.PROTECT)
    supplier = models.ForeignKey(Supplier, verbose_name=_(u'supplier'), on_delete=models.PROTECT)
    issue_date = models.DateField(verbose_name=_(u'issue date'))
    required_date = models.DateField(null=True, blank=True, verbose_name=_(u'date required'))
    state = models.CharField(max_length=16, default='draft', choices=[('draft', _('Draft')), ('pending', _('Pending')), ('done', _('Done')), ('reject', _('Rejected'))])
    #active = models.BooleanField(default=True, verbose_name=_(u'active'))
    notes = models.TextField(null=True, blank=True, verbose_name=_(u'notes'))
    status = models.ForeignKey(PurchaseOrderStatus, null=True, blank=True, verbose_name=_(u'status'), on_delete=models.PROTECT)
    department = models.ForeignKey(Department, verbose_name=_("corresponding department"),
                blank=True, null=True, related_name='+', on_delete=models.SET_NULL)

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

    def map_items(self):
        """ Map the items mentioned in this PO to real items inside the PO's movements

            This will also provide the dataset that will fill further movements

              loc_kind: {item_template: [obj( id, parent_id, serial|False, item_id|False),...] }

            where:
                loc_kind: kind of location: 'bdl' for the bundle location, <tmpl_id>
                    when the item's category has a chained template or '' for the generic
                    location
                id, parent_id: arbitrary addressing of PO item ids
                item_id: an asset.Item id
        """
        logger = logging.getLogger('apps.movements.PurchaseOrder.calc')

        ret = defaultdict(lambda: defaultdict(list)) # default dict-in-dict
        logger.debug('map_items(): first stage for %s', self.id)
        # 1st step: fill dicts with the things we've ordered
        for item in self.items.all():
            if not item.received_qty:
                continue

            if not item.item_template_id:
                raise ValueError(_('Item template for item "%s" has not been assigned. Cannot continue.'), item.item_name)

            if item.item_template.category.is_group and not item.item_template.category.is_bundle:
                # Skip group containers. We never receive them as items
                continue

            # find appropriate location
            if item.in_group:
                loc_kind = 'bdl'
            elif item.item_template.category.chained_location:
                loc_kind = item.item_template.category.chained_location_id
            else:
                loc_kind = ''

            # build list of new serial numbers
            serials = []
            for s in item.serial_nos.replace('\n', ',').split(','):
                s = s.strip()
                if s:
                    serials.append(s)
            if item.received_qty < len(serials):
                raise ValueError(_("You have given %(slen)d serials, but marked only %(received)d received items. Please fix either of those") % \
                        dict(slen=len(serials), received=item.received_qty))
            iid = item.item_template_id

            # locate the entry in 'ret' about our case
            oldlist = ret[loc_kind][iid]

            old_serials = set([o.serial for o in oldlist])
            # This is an error, because we cannot allow different PO lines to repeat
            # the same serials for the same products.
            assert not old_serials.intersection(serials), \
                    "Some serials are repeated in po: %s "  % \
                        ','.join(old_serials.intersection(serials))

            rec_qty = item.received_qty
            idx = 0
            parent_id = None
            if item.in_group:
                parent_id = (item.in_group, 1)  # We expect group.qty == 1, so always map
                                                # to the first item
            for idx, s in enumerate(serials):
                oldlist.append(_map_item((item.id, idx), parent_id=parent_id, serial=s))
                for bid in item.bundled_items.all():
                    for i in range(bid.qty):
                        ret['bdl'][bid.item_template_id].append( \
                                _map_item((bid.id,idx,i), parent_id=(item.id, idx)) )
                rec_qty -= 1

            while rec_qty > 0:
                idx += 1
                oldlist.append(_map_item((item.id, idx), parent_id=parent_id))
                for bid in item.bundled_items.all():
                    for i in range(bid.qty):
                        ret['bdl'][bid.item_template_id].append( \
                                _map_item((bid.id,idx,i), parent_id=(item.id, idx)) )
                rec_qty -= 1

        logger.debug('map_items(): second stage for %s', self.id)
        def _consume(item, loc_kind):
            """ given a movement item, find which part of 'ret' it can be mapped to
            """
            assert item.qty == 1, item.qty
            if loc_kind not in ret:
                return False
            olist = ret[loc_kind].get(item.item_template_id, [])
            for mo in olist:
                if mo.item_id:
                    # already mapped
                    continue
                if mo.serial != item.serial_number:
                    continue
                mo.item_id = item.id
                return True

            return False

        for move in self.movements.prefetch_related('items').all(): # requires Django 1.4
            # Prefetching the items is crucial, it will reduce Queries done
            if move.location_dest.usage == 'production':
                loc_kind = 'bdl'
            elif move.location_dest.template is not None:
                loc_kind = move.location_dest.template_id
            else:
                loc_kind = ''

            for item in move.items.iterator():
                if _consume(item, loc_kind):
                    continue
                if loc_kind not in ('bdl', ''):
                    # second attempt, to generic location
                    if _consume(item, ''):
                        continue
                logger.debug("Movement %d, item not consumed in %s: %r", move.id, loc_kind, item)

        return ret

    def map_has_left(self, mapped_items):
        for tdict in mapped_items.values():
            for objs in tdict.values():
                for o in objs:
                    if not o.item_id:
                        return True
        return False

    def items_into_moves(self, mapped_items, request, department, master_location):
        """ Generate moves for mapped items
        """

        the_moves = {}
        def _get_move(loc_kind):
            if loc_kind in the_moves:
                return the_moves[loc_kind]

            lsrcs = Location.objects.filter(department__isnull=True, usage='procurement')[:1]
            if not lsrcs:
                msg = _(u'There is no procurement location configured in the system!')
                messages.error(request, msg, fail_silently=True)
                raise RuntimeError

            if loc_kind == 'bdl':
                ldests = Location.objects.filter(department__isnull=True, usage='production')[:1]
                if not ldests:
                    msg = _(u'This is not bundling location configured in the system!')
                    messages.error(request, msg, fail_silently=True)
                    raise RuntimeError
            elif loc_kind == '':
                ldests = [master_location,]
                if not master_location:
                    msg = _(u'This is not default department and location for this user, please fix!')
                    messages.error(request, msg, fail_silently=True)
                    raise RuntimeError
            else:
                # must be a location template_id
                ldests = Location.objects.filter(department=department, template_id=loc_kind, usage='internal')[:1]
                if not ldests:
                    ltmpl = LocationTemplate.objects.get(pk=loc_kind)
                    msg = _("Department %(dept)s does not have a location for \"%(loc)s\" to store items") % \
                            { 'dept': unicode(department), 'loc': unicode(ltmpl) }
                    messages.error(request, msg, fail_silently=True)
                    raise RuntimeError
            movement, c = Movement.objects.get_or_create( stype='in', origin=self.user_id,
                    location_src=lsrcs[0], location_dest=ldests[0],
                    purchase_order=self,
                    defaults=dict(create_user=request.user,date_act=self.issue_date, ))
            movement.save()
            the_moves[loc_kind] = movement
            return movement

        id_map = {}
        for lk, it_tmpls in mapped_items.items():
            for tmpl_id, objs in it_tmpls.items():
                for o in objs:
                    if not o.item_id:
                        move = _get_move(lk)
                        if o.serial:
                            new_item, c = Item.objects.get_or_create(item_template_id=tmpl_id,
                                        serial_number=o.serial)
                        else:
                            new_item = Item(item_template_id=tmpl_id)
                        new_item.save()
                        move.items.add(new_item)
                        o.item_id = new_item.id

                    if o.id in id_map:
                        # inserted early by parent setdefault()
                        assert id_map[o.id][0] is False, id_map[o.id]
                        id_map[o.id] = (o.item_id, id_map[o.id][1])
                    else:
                        id_map[o.id] = (o.item_id, [])
                    if o.parent_id:
                        id_map.setdefault(o.parent_id, (False, []))[1].append(o.item_id)

        # Restore bundle relations. The id_map should have provided us with concrete
        # information..
        for item_id, children in id_map.values():
            if not children:
                continue
            if item_id is False:
                # the case where is_group == True, is_bundle == False
                # then, we want the child to be standalone
                for citem in Item.objects.filter(pk__in=children):
                    if list(citem.bundled_in.exists()):
                        citem.bundled_in.clear()
                        citem.is_bundled = False

            bitem = Item.objects.get(pk=item_id)
            igroup, c = ItemGroup.objects.get_or_create(item_ptr=bitem,
                                defaults={'item_template': bitem.item_template })
            if c:
                bitem.save()
            for citem in Item.objects.filter(pk__in=children):
                if list(citem.bundled_in.all()) != [bitem,]:
                    citem.bundled_in.clear()
                    citem.bundled_in.add(igroup)
                    citem.is_bundled = True
                    citem.save()
        return True

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
        if self.state != 'draft':
            raise ValidationError(_("Cannot add items to this Purchase Order"))
        if obj is None or not isinstance(obj, ItemTemplate):
            raise TypeError(_("Incorrect object passed: %s") % repr(obj))

        self.items.create(item_template=obj, received_qty=1)
        return 'added'

    def remove_from_cart(self, obj):
        # FIXME: we may want to disable this function entirely
        if self.state != 'draft':
            raise ValidationError(_("Cannot add items to this Purchase Order"))
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

    def do_reject(self, user):
        """Reject all movements of this PO and mark self as done
        """
        if self.movements.filter(state='done').exists():
            raise ValueError(_("Cannot reject a Purchase Order that contains any moves in done state!"))

        self.movements.exclude(state='reject').update(state='reject', validate_user=user)
        self.state = 'reject'
        self.validate_user = user
        self.save()
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
    item_template = models.ForeignKey(ItemTemplate, verbose_name=_(u'item template'), null=True, blank=True, on_delete=models.PROTECT)
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
    item_template = models.ForeignKey(ItemTemplate, verbose_name=_(u'item template'), null=True, blank=True, on_delete=models.PROTECT)
    qty = models.PositiveIntegerField(default=1, verbose_name=_(u'quantity'))

    class Meta:
        verbose_name = _(u'bundled item')
        verbose_name_plural = _(u'bundled items')

    def __unicode__(self):
        return unicode(self.item_template)

class RepairOrderManager(models.Manager):
    def by_request(self, request):
        Q = models.Q
        try:
            if request.user.is_superuser:
                return self.all()
            else:
                active_role = role_from_request(request)
                if active_role:
                    q = Q(department=active_role.department)
                else:
                    q = Q(create_user=request.user) | Q(validate_user=request.user) \
                        | Q(department__in=request.user.dept_roles.values_list('department', flat=True))
                return self.filter(q)
        except Exception:
            logger.exception("cannot filter:")
        return self.none()

class RepairOrder(models.Model):
    objects = RepairOrderManager()
    item = models.ForeignKey(ItemGroup, verbose_name=_("Item"), on_delete=models.PROTECT)
    user_id = models.CharField(max_length=32, null=True, blank=True, verbose_name=_(u'user defined id'))
    create_user = models.ForeignKey('auth.User', related_name='+', verbose_name=_("created by"), on_delete=models.PROTECT)
    validate_user = models.ForeignKey('auth.User', blank=True, null=True, related_name='+', verbose_name=_("validated by"), on_delete=models.PROTECT)
    issue_date = models.DateField(verbose_name=_(u'issue date'))
    #active = models.BooleanField(default=True, verbose_name=_(u'active'))
    state = models.CharField(max_length=16, default='draft', choices=[('draft', _('Draft')), ('pending', _('Pending')), ('done', _('Done')), ('reject', _('Rejected'))])
    notes = models.TextField(null=True, blank=True, verbose_name=_(u'notes'))
    department = models.ForeignKey(Department, verbose_name=_("corresponding department"),
                blank=True, null=True, related_name='+', on_delete=models.SET_NULL)

    class Meta:
        verbose_name = _(u'repair order')
        verbose_name_plural = _(u'repair orders')
        permissions = ( ('validate_repairorder', 'Can validate a repair order'), )

    def __unicode__(self):
        return '#%s (%s)' % (self.user_id if self.user_id else self.id, self.issue_date)

    @models.permalink
    def get_absolute_url(self):
        return ('repair_order_view', [str(self.id)])

    def do_close(self, user):
        """ Update the the items bound in the itemgroup

            You *must* call movements[].do_close() before this
        """
        bundle_location = Location.objects.filter(department__isnull=True, usage='production')[:1][0]

        itemgroup = self.item.itemgroup
        for move in self.movements.all():
            if move.state != 'done':
                # caller forgot to close it!
                raise ValueError("Movement is not validated")
            if move.location_dest == bundle_location:
                # items added to the bundle
                for it in move.items.all():
                    itemgroup.items.add(it)
                move.items.update(is_bundled=True)
            elif move.location_src == bundle_location:
                # items removed from the bundle
                for it in move.items.all():
                    itemgroup.items.remove(it)
                move.items.update(is_bundled=False)
            else:
                raise ValueError(u"Invalid move #%d %s for a Repair Order" % (move.id, unicode(move)))

        self.validate_user = user
        self.state = 'done'
        self.save()
        return True

    def do_reject(self, user):
        """Reject all movements of this RO and mark self as done
        """
        for move in self.movements.all():
            if move.state not in ('draft', 'pending'):
                raise ValueError(_("Cannot reject a Purchase Order that contains any moves in %s state!") % \
                    move.get_state_display() )

        self.movements.update(state='reject', validate_user=user)
        self.state = 'reject'
        self.validate_user = user
        self.save()
        return True

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
            default=datetime.date.today,
            help_text=_("Format: 23/04/2010"))
    date_val = models.DateField(verbose_name=_(u'date validated'), blank=True, null=True)
    create_user = models.ForeignKey('auth.User', related_name='+', verbose_name=_('created by'), on_delete=models.PROTECT)
    validate_user = models.ForeignKey('auth.User', blank=True, null=True, related_name='+', verbose_name=_('validated by'), on_delete=models.PROTECT)
    src_date_val = models.DateField(verbose_name=_(u'date source validated'), blank=True, null=True)
    src_validate_user = models.ForeignKey('auth.User', blank=True, null=True, related_name='+', verbose_name=_('source validated by'), on_delete=models.PROTECT)

    name = models.CharField(max_length=32, blank=True, verbose_name=_(u'reference'))
    state = models.CharField(max_length=16, default='draft', choices=[('draft', _('Draft')), ('pending', _('Pending')), ('done', _('Done')), ('reject', _('Rejected'))])
    stype = models.CharField(max_length=16, choices=[('in', _('Incoming')),('out', _('Outgoing')),
                ('internal', _('Internal')), ('other', _('Other'))], verbose_name=_('type'))
    origin = models.CharField(max_length=64, blank=True, verbose_name=_('origin'))
    note = models.TextField(verbose_name=_('Notes'), blank=True)
    location_src = models.ForeignKey(Location, related_name='location_src', verbose_name=_("source location"), on_delete=models.PROTECT)
    location_dest = models.ForeignKey(Location, related_name='location_dest', verbose_name=_("destination location"), on_delete=models.PROTECT)
    items = models.ManyToManyField(Item, verbose_name=_('items'), related_name='movements', blank=True)
    # limit_choices_to these at location_src

    checkpoint_src = models.ForeignKey('inventory.Inventory', verbose_name=_('Source checkpoint'),
                null=True, blank=True, related_name='+', on_delete=models.SET_NULL)
    checkpoint_dest = models.ForeignKey('inventory.Inventory', verbose_name=_('Destination checkpoint'),
                null=True, blank=True, related_name='+', on_delete=models.SET_NULL)

    purchase_order = models.ForeignKey(PurchaseOrder, blank=True, null=True, related_name='movements', on_delete=models.SET_NULL)
    repair_order = models.ForeignKey(RepairOrder, blank=True, null=True, related_name='movements', on_delete=models.SET_NULL)

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
        if self.location_src_id and (self.location_src_id == self.location_dest_id):
            raise ValidationError(_("A movement cannot have the same source and destination locations!"))

        if self.location_dest_id and self.location_dest.usage in 'internal':
            locs.append(self.location_dest)
        if self.location_src_id and self.location_src.usage in 'internal':
            locs.append(self.location_src)

        if locs:
            # find if there is any validated inventory for either location,
            # use it as checkpoint_src
            chks = Inventory.objects.filter(location__in=locs, state='done'). \
                        order_by('-date_act')[:1]
            if chks:
                self.checkpoint_src = chks[0]

    def _close_check(self):
        if self.state not in ('draft', 'pending'):
            raise ValueError(_("Cannot close movement %(move)s (id: %(mid)s) because it is not in draft state") % dict(move=self.name, mid=self.id))
        if self.date_val:
            raise ValueError(_("Cannot close movement because it seems already validated!"))

        if self.checkpoint_dest is not None:
            raise ValueError(_("Internal error, movement is already checkpointed"))

        self.clean()
        if self.checkpoint_src and self.date_act < self.checkpoint_src.date_val:
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

            if self.location_dest.department \
                        and item.item_template.category.chained_location \
                        and item.item_template.category.chained_location != self.location_dest.template:
                raise ValueError(_("Item of category %(category)s cannot be moved into a %(template)s location. " \
                                "\nSuch an item is only allowed in %(allow_tmpl)s locations" ) %\
                        { 'category': unicode(item.item_template.category.name),
                          'template': unicode(self.location_dest.template or _('generic')),
                          'allow_tmpl': unicode(item.item_template.category.chained_location) })

        if self.stype == 'in' and self.purchase_order_id and self.purchase_order.procurement_id:
            all_items.update(src_contract=self.purchase_order.procurement)

        return True

    def do_close(self, val_user, val_date=None):
        """Check the items and set the movement as 'done'

        This function does the most important processing of a movement. It will
        check the integrity of all contained data, and then update the inventories
        accordingly.
        """
        if val_date is None:
            val_date = datetime.date.today()

        self._close_check()

        all_items = self.items.all()
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

    def do_reject(self, rej_user):
        """Mark movement as rejected. No assets will change, move will be locked
        
            The rejection should be performed no matter what the state of the
            contained items are. But we still need to check that this move was
            really open (and not checkpointed) before.
        """
        if self.state not in ('draft', 'pending') or self.date_val:
            raise ValueError(_("Cannot reject movement %(move)s (id: %(mid)s) because it is not in open state") % dict(move=self.name, mid=self.id))

        if self.checkpoint_dest is not None:
            raise ValueError(_("Internal error, movement is already checkpointed"))

        self.clean()
        self.validate_user = rej_user
        self.date_val = datetime.date.today()
        self.state = 'reject'
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
        if self.state != 'draft':
            raise ValueError(_("Cannot modify items of this move"))
        if self.date_val is not None or self.validate_user is not None \
                    or self.src_validate_user:
            raise ValueError(_("Cannot modify items of a validated move"))
        if obj is None or not isinstance(obj, Item):
            raise TypeError(_("Incorrect object passed: %s") % repr(obj))

        if self.items.filter(id=obj.id).exists():
            raise ValueError(_("Item already in movement"))

        self.items.add(obj)
        return 'added'

    def remove_from_cart(self, obj):
        if self.state != 'draft':
            raise ValueError(_("Cannot modify items of this move"))
        if self.date_val is not None or self.validate_user is not None \
                    or self.src_validate_user:
            raise ValueError(_("Cannot modify items of a validated move"))
        if obj is None or not isinstance(obj, Item):
            raise TypeError(_("Incorrect object passed: %s") % repr(obj))

        done = False
        try:
            self.items.remove(obj)
            done = True
        except Exception, e:
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
