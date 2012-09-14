from django.db import models
from django.utils.translation import ugettext_lazy as _
from dynamic_search.api import register

from common.models import Partner, Supplier

class ItemCategory(models.Model):
    name = models.CharField(max_length=64)
    parent = models.ForeignKey("ItemCategory", related_name="+", blank=True, null=True)

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
    applies_category = models.ManyToManyField(ItemCategory, related_name="applies_cat")
    max_entries = models.IntegerField()
    optional = models.BooleanField()
    in_name = models.BooleanField()
    

class AbstractAttribute(models.Model):
    """Extra properties an Item can have
    
        Examples: "weight=10kg" in packages, "RAM=512MB" in PCs etc.
    """
    atype = models.ForeignKey(ItemAttrType, verbose_name=_(u"attribute"))
    value = models.CharField(max_length=32)

    class Meta:
        abstract = True

class Manufacturer(Partner):
    #TODO: Contact, extension
    # just put any field here, for db:
    country = models.CharField(max_length=32, null=True, blank=True, 
        verbose_name=_("country of origin"), )

    class Meta:
        ordering = ['name']

class ItemTemplate(models.Model):
    description = models.CharField(verbose_name=_(u"description"), max_length=64)
    category = models.ForeignKey(ItemCategory,)
    brand = models.CharField(verbose_name=_(u"brand"), max_length=32, null=True, blank=True, 
        help_text=_("Brand name, if different from manufacturer"))
    manufacturer = models.ForeignKey(Manufacturer, )
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

class ItemTemplateAttribute(AbstractAttribute):
    template = models.ForeignKey(ItemTemplate, related_name="attributes")

register(ItemTemplate, _(u'templates'), ['description', 'brand', 'model', 'part_number', 'notes'])

#eof
