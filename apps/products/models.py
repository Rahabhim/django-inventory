# -*- encoding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _
from dynamic_search.api import register

from common.models import Partner, Supplier

class ItemCategory(models.Model):
    name = models.CharField(max_length=64, verbose_name=_("Name"))
    parent = models.ForeignKey("ItemCategory", related_name="+", blank=True, null=True,
                verbose_name=_("parent category"))
    approved = models.BooleanField(default=False, verbose_name=_("approved"))
    is_bundle = models.BooleanField(default=False, verbose_name=_("Is bundle"))

    @models.permalink
    def get_absolute_url(self):
        return ('category_view', [str(self.id)])

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name=_("item category")

class ItemCategoryContain(models.Model):
    parent_category = models.ForeignKey(ItemCategory, related_name="may_contain", verbose_name=_("May contain"))
    category = models.ForeignKey(ItemCategory, related_name='+', verbose_name=_("contained category"))
    min_count = models.IntegerField(verbose_name=_("minimum count"), default=0)
    max_count = models.IntegerField(verbose_name=_("maximum count"), default=1)

    def __unicode__(self):
        return self.category.name

class ItemAttrType(models.Model):
    """
    
        @attr max_entries If > 0, defines the maximum repetitions of such an
            attribute for any item in the category
        @attr optional If false, at least 1 such attribute must exist (and up to
            max_entries
        @attr in_name If True, the attribute will be appended in Item's name
    """
    unit = models.CharField(max_length=64, verbose_name=_("units"), blank=True, null=True,
            choices = [('weight', 'kg'), ('memsize', 'MB'), ('cpuspeed', 'MHz'),
                ('color', 'Color')])
    name = models.CharField(max_length=64, verbose_name=_("name"),
            blank=False)
    applies_category = models.ManyToManyField(ItemCategory, related_name="applies_cat", 
            blank=True, null=True)
    max_entries = models.IntegerField()
    optional = models.BooleanField()
    in_name = models.BooleanField()

    def __unicode__(self):
        return self.name


class AbstractAttribute(models.Model):
    """Extra properties an Item can have
    
        Examples: "weight=10kg" in packages, "RAM=512MB" in PCs etc.
    """
    atype = models.ForeignKey(ItemAttrType, verbose_name=_(u"attribute"))
    value = models.CharField(max_length=32)

    def __unicode__(self):
        return '%s=%s' % (self.atype.name, self.value)

    class Meta:
        abstract = True

class Manufacturer(Partner):
    #TODO: Contact, extension
    # just put any field here, for db:
    country = models.CharField(max_length=32, null=True, blank=True, 
        verbose_name=_("country of origin"), )

    class Meta:
        ordering = ['name']

    @models.permalink
    def get_absolute_url(self):
        return ('manufacturer_view', [str(self.id)])

    def __unicode__(self):
        return self.name

class ItemTemplate(models.Model):
    description = models.CharField(verbose_name=_(u"description"), max_length=256)
    category = models.ForeignKey(ItemCategory,)
    approved = models.BooleanField(default=False)
    brand = models.CharField(verbose_name=_(u"brand"), max_length=32, null=True, blank=True, 
        help_text=_("Brand name, if different from manufacturer"))
    manufacturer = models.ForeignKey(Manufacturer, related_name="products")
    model = models.CharField(verbose_name=_(u"model"), max_length=32, null=True, blank=True)
    part_number = models.CharField(verbose_name=_(u"part number"), max_length=32, null=True, blank=True)
    notes = models.TextField(verbose_name=_(u"notes"), null=True, blank=True)
    supplies = models.ManyToManyField("self", null=True, blank=True, verbose_name=_(u"supplies"))
    suppliers = models.ManyToManyField(Supplier, null=True, blank=True)

    class Meta:
        ordering = ['description']
        verbose_name = _(u"item template")
        verbose_name_plural = _(u"item templates")

    @models.permalink
    def get_absolute_url(self):
        return ('template_view', [str(self.id)])

    def __unicode__(self):
        return self.description

    def validate_bundle(self, bundled_items):
        """Validates that this bundle is assembled according to category rules

            @param bundled_items a list of (ItemCategory.id, qty) tuples
            @return [] if valid, or a list of error messages
        """
        errors = []
        self_cat = self.category
        if self_cat.is_bundle:
            if not bundled_items:
                bundled_items = [] # just in case it was None or False

            haz_it = {}
            for catid, qty in bundled_items:
                if catid in haz_it:
                    haz_it[catid] += qty
                else:
                    haz_it[catid] = qty

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
                    errors.append(err_msg % {'self_cat': self_cat.name, 'sub_cat': subcat.category.name, \
                            'min_count': subcat.min_count, 'max_count': subcat.max_count})
            if haz_it:
                err_msg = _("An item of %(self_cat)s cannot contain any items of %(sub_cat)s.")
                for subcat in ItemCategory.objects.filter(pk__in=haz_it.keys()):
                    errors.append(err_msg % {'self_cat': self_cat.name, 'sub_cat': subcat.name})
        elif bundled_items:
            # it is not a bundle, don't allow bundled items
            errors.append(_("An item of %s is not a bundle, cannot contain anything") % \
                    self_cat.name)
        return errors

class ItemTemplateAttribute(AbstractAttribute):
    template = models.ForeignKey(ItemTemplate, related_name="attributes")

register(ItemTemplate, _(u'templates'), ['description', 'brand', 'model', 'part_number', 'notes'])

#eof
