# -*- encoding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _
from dynamic_search.api import register
from collections import defaultdict

from common.models import Partner, PartnerManager, Supplier

class ItemCategory(models.Model):
    name = models.CharField(max_length=64, verbose_name=_("Name"))
    sequence = models.IntegerField(default=10, verbose_name=_("sequence"))
    parent = models.ForeignKey("ItemCategory", related_name="+", blank=True, null=True,
                verbose_name=_("parent category"), on_delete=models.PROTECT)
    approved = models.BooleanField(default=False, verbose_name=_("approved"))
    is_bundle = models.BooleanField(default=False, verbose_name=_("Is bundle"))
    is_group = models.BooleanField(default=False, verbose_name=_("Is set"))
    use_serials = models.BooleanField(default=True, verbose_name=_("Items have serials"))
    picture = models.ImageField(verbose_name=_("Picture"), upload_to='categories', 
                blank=True, null=True)
    chained_location = models.ForeignKey('common.LocationTemplate', verbose_name=_('Chained location'),
                blank=True, null=True)

    @models.permalink
    def get_absolute_url(self):
        return ('category_view', [str(self.id)])

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name=_("item category")
        verbose_name_plural = _("item categories")
        ordering = ['name',]

    @property
    def categ_class(self):
        """behavior of the category, in one word"""
        if self.is_group and self.is_bundle:
            return 'bundle-group'
        elif self.is_group:
            return 'group'
        elif self.is_bundle:
            return 'bundle'
        elif self.contained_in.filter(parent_category__is_group=False).exists():
            return 'part'
        else:
            return 'equipment'

class ItemCategoryContain(models.Model):
    parent_category = models.ForeignKey(ItemCategory, related_name="may_contain", verbose_name=_("May contain"), on_delete=models.PROTECT)
    category = models.ForeignKey(ItemCategory, related_name='contained_in', verbose_name=_("contained category"))
    min_count = models.IntegerField(verbose_name=_("minimum count"), default=0)
    max_count = models.IntegerField(verbose_name=_("maximum count"), default=1)

    def __unicode__(self):
        return self.category.name

class ProductAttribute(models.Model):
    """Extra properties an ItemTemplate can have
    
        Properties will be chosen from a finite set
    """

    name = models.CharField(max_length=64, verbose_name=_("name"))
    short_name = models.CharField(max_length=16, verbose_name=_("short name"), blank=True)
    sequence = models.IntegerField(default=10, verbose_name=_("sequence"))
    
    applies_category = models.ForeignKey(ItemCategory, related_name="attributes",
                    verbose_name=_("category"), on_delete=models.PROTECT)
    required = models.BooleanField(default=True, verbose_name=_("required"))
    in_name = models.BooleanField(default=False, verbose_name=_("include in name"))

    def __unicode__(self):
        return '%s: %s' % (self.applies_category.name, self.name)

    @models.permalink
    def get_absolute_url(self):
        return ('attributes_view', [str(self.id)])

    class Meta:
        verbose_name=_("attribute")
        verbose_name_plural=_("attributes")
        ordering = ['sequence', 'name']

class ProductAttributeValue(models.Model):
    """Allowed value for some ProductAttribute
    """
    atype = models.ForeignKey(ProductAttribute, verbose_name=_(u"attribute"), \
                    related_name="values", on_delete=models.PROTECT)
    value = models.CharField(max_length=32, verbose_name=_("value"))
    value_num = models.FloatField(verbose_name=_("numeric value"), blank=True, null=True)

    def __unicode__(self):
        if self.atype.short_name:
            if self.atype.short_name[-1].isalnum():
                ch = '='
            else:
                ch = ''
            return '%s%s%s' % (self.atype.short_name, ch, self.value)
        else:
            return self.value

    class Meta:
        verbose_name=_("attribute value")
        verbose_name_plural=_("attribute values")
        ordering = ['atype', 'value']

class Manufacturer(Partner):
    #TODO: Contact, extension
    # just put any field here, for db:
    objects = PartnerManager()
    country = models.CharField(max_length=32, null=True, blank=True, 
        verbose_name=_("country of origin"), )

    class Meta:
        ordering = ['name']
        verbose_name = _("manufacturer")
        verbose_name_plural = _("manufacturers")

    @models.permalink
    def get_absolute_url(self):
        return ('manufacturer_view', [str(self.id)])

    def __unicode__(self):
        return self.name

class ItemTemplateManager(models.Manager):
    def by_request(self, request):
        if request.user.is_superuser or request.user.is_staff:
            return self.all()
        else:
            return self.filter(approved=True)

class ItemTemplate(models.Model):
    objects = ItemTemplateManager()
    description = models.CharField(verbose_name=_(u"description"), max_length=256)
    category = models.ForeignKey(ItemCategory, verbose_name=_("category"), on_delete=models.PROTECT)
    approved = models.BooleanField(default=False, verbose_name=_("approved"))
    brand = models.CharField(verbose_name=_(u"brand"), max_length=32, null=True, blank=True, 
        help_text=_("Brand name, if different from manufacturer"))
    manufacturer = models.ForeignKey(Manufacturer, related_name="products", verbose_name=_("manufacturer"), on_delete=models.PROTECT)
    model = models.CharField(verbose_name=_(u"model"), max_length=32, null=True, blank=True)
    part_number = models.CharField(verbose_name=_(u"part number"), max_length=32, null=True, blank=True)
    url = models.CharField(verbose_name=_("URL"), max_length=256, null=True, blank=True)
    notes = models.TextField(verbose_name=_(u"notes"), null=True, blank=True)
    supplies = models.ManyToManyField("self", null=True, blank=True, verbose_name=_(u"supplies"))
    suppliers = models.ManyToManyField(Supplier, null=True, blank=True, verbose_name=_("suppliers"))

    class Meta:
        ordering = ['description']
        verbose_name = _(u"item template")
        verbose_name_plural = _(u"item templates")

    @models.permalink
    def get_absolute_url(self):
        return ('template_view', [str(self.id)])

    def __unicode__(self):
        ret = self.description
        try:
            for attr in self.attributes.filter(value__atype__in_name=True):
                ret += ' ' + unicode(attr.value)
        except Exception:
            pass
        return ret

    def validate_bundle(self, bundled_items, flat=True, group_mode=False):
        """Validates that this bundle/group is assembled according to category rules

            @param bundled_items a list of (ItemCategory.id, qty) tuples
            @param flat Return all errors in one list, rather than dict(cat=)
            @return empty if valid, a list of error messages when flat=True, or
                    a dict of lists of errors, having key=category
        """
        errors = defaultdict(list)
        self_cat = self.category
        if group_mode:
            iz_group = self_cat.is_group
        else:
            iz_group = self_cat.is_bundle
        if iz_group:
            if not bundled_items:
                bundled_items = [] # just in case it was None or False

            haz_it = defaultdict(int)
            for catid, qty in bundled_items:
                haz_it[catid] += qty

            for subcat in self_cat.may_contain.all():
                err_msg = False
                haz = haz_it.pop(subcat.category_id, 0)
                if haz < subcat.min_count:
                    if haz:
                        err_msg = _("An item of %(self_cat)s must contain at least %(min_count)d of %(sub_cat)s, but only has %(count)d now.")
                    else:
                        err_msg = _("An item of %(self_cat)s must contain at least %(min_count)d of %(sub_cat)s.")
                elif haz > subcat.max_count:
                    err_msg = _("An item of %(self_cat)s cannot have more than %(max_count)d of %(sub_cat)s. You have entered %(count)d.")

                if err_msg:
                    errors[subcat.category_id].append(err_msg % {'self_cat': self_cat.name, 'sub_cat': subcat.category.name, \
                            'count': haz, 'min_count': subcat.min_count, 'max_count': subcat.max_count})
            if haz_it:
                err_msg = _("An item of %(self_cat)s cannot contain any items of %(sub_cat)s.")
                for subcat in ItemCategory.objects.filter(pk__in=haz_it.keys()):
                    errors['*'].append(err_msg % {'self_cat': self_cat.name, 'sub_cat': subcat.name})
        elif bundled_items:
            # it is not a bundle, don't allow bundled items
            if group_mode:
                estr = _("An item of %s is not a group, cannot have contained items")
            else:
                estr = _("An item of %s is not a bundle, cannot contain anything")
            errors['*'].append( estr % self_cat.name)
        if flat:
            if errors:
                return reduce(lambda a,b: a+b, errors.values())
            else:
                return []
        else:
            return errors

class ItemTemplatePart(models.Model):
    parent = models.ForeignKey(ItemTemplate, verbose_name=_("parent"), related_name="parts", on_delete=models.CASCADE)
    item_template = models.ForeignKey(ItemTemplate, verbose_name=_("template"), on_delete=models.PROTECT)
    qty = models.IntegerField(verbose_name=_("Quantity"))

    class Meta:
        verbose_name = _("part")
        verbose_name_plural = _("standard parts")

class ItemTemplateAttributes(models.Model):
    template = models.ForeignKey(ItemTemplate, related_name="attributes", on_delete=models.CASCADE)
    value = models.ForeignKey(ProductAttributeValue, verbose_name=_("value"), on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("attribute")
        verbose_name_plural = _("attributes")
        ordering = ['value__atype__sequence', 'value__atype__name']

class ItemTemplateNumAlias(models.Model):
    parent = models.ForeignKey(ItemTemplate, verbose_name=_("parent"), related_name="pn_aliases", on_delete=models.CASCADE)
    part_number = models.CharField(verbose_name=_(u"part number"), max_length=32, null=True, blank=True)

    class Meta:
        verbose_name = _("alias part number")
        verbose_name_plural = _("alias part numbers")

register(ItemTemplate, _(u'templates'), ['description', 'brand', 'model', 'part_number', 'notes'])

#eof
