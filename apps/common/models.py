# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models
from django.utils.translation import ugettext_lazy as _
from dynamic_search.api import register
from django.core.exceptions import ValidationError, ObjectDoesNotExist

class Partner(models.Model):
    name = models.CharField(max_length=128, db_index=True, unique=True, verbose_name=_("name"))
    active = models.BooleanField(verbose_name=_("active"), default=False)
    web = models.CharField(max_length=128, blank=True, null=True)
    comment = models.TextField(blank=True, null=True, verbose_name=_("comment"))
    # category = 

    class Meta:
        ordering = ['name']
        verbose_name = _("partner")

    def __unicode__(self):
        return self.name


class Address(models.Model):
    name = models.CharField(max_length=128, verbose_name=_("contact"))
    partner = models.ForeignKey(Partner, db_index=True, verbose_name=_("partner"))
    address = models.TextField(blank=True, null=True, verbose_name=_("address"))
    active = models.BooleanField(verbose_name=_("active"), default=False)
    phone1 = models.CharField(max_length=32, verbose_name=_("phone"), blank=True, null=True)
    phone2 = models.CharField(max_length=32, verbose_name=_("phone 2"), blank=True, null=True)


    def __unicode__(self):
        return self.name
    
    class Meta:
        verbose_name = _("address")
        verbose_name_plural = _("addresses")

class LocationTemplate(models.Model):
    """ A location template is just names of locations to create for each dpt. type

    """
    name = models.CharField(max_length=32, verbose_name=_("name"))
    sequence = models.IntegerField(verbose_name=_("sequence"), default=10)

    class Meta:
        ordering = ['sequence', 'name']
        verbose_name = _(u"location template")
        verbose_name_plural = _(u"location templates")

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('location_template_view', [str(self.id)])


class Location(models.Model):
    """
    
        The usage is modelled after the OpenERP values.
        inventory is a virtual location, used to correct stock levels
    """
    name = models.CharField(max_length=32, verbose_name=_("name"), db_index=True)
    sequence = models.IntegerField(verbose_name=_("sequence"), default=10)
    department = models.ForeignKey('company.Department', null=True, blank=True, verbose_name=_("department"))

    usage = models.CharField(max_length=32, verbose_name=_("location type"),
            choices=[('customer', _('Customer')), ('procurement', _('Procurement')), 
                    ('internal', _('Internal')), ('inventory', _('Inventory')), 
                    ('supplier', _('Supplier Location')), ('production', _('Bundled'))])

    class Meta:
        ordering = ['sequence', 'name']
        verbose_name = _(u"location")
        verbose_name_plural = _(u"locations")

    def __unicode__(self):
        ret = ''
        if self.department:
            ret = self.department.name + ' / '
        ret += self.name
        return ret

    @models.permalink
    def get_absolute_url(self):
        return ('location_view', [str(self.id)])

    def clean(self):
        if self.department and self.usage != 'internal':
            raise ValidationError("Department can only be specified for \"internal\" locations")
        return super(Location, self).clean()

    def get_sequence(self):
        if self.department:
            return self.department.get_sequence()
        else:
            raise ObjectDoesNotExist("No department for location %s" % self.name)

class Supplier(Partner):
    #TODO: Contact, extension
    vat_number = models.CharField(max_length=32, null=True, blank=True, verbose_name=_("VAT number"))

    class Meta:
        ordering = ['name']
        verbose_name = _(u"supplier")
        verbose_name_plural = _(u"suppliers")


    @models.permalink
    def get_absolute_url(self):
        return ('supplier_view', [str(self.id)])

class Sequence(models.Model):
    name = models.CharField(max_length=64, verbose_name=_("name"))
    prefix = models.CharField(verbose_name=_('prefix'), max_length=64, blank=True)
    suffix = models.CharField(verbose_name=_('suffix'), max_length=64, blank=True)
    number_next = models.IntegerField(verbose_name=_('next number'), default=1)
    number_increment = models.IntegerField(verbose_name=_('increment'), default=1)
    padding = models.IntegerField(verbose_name=_('Number padding'), default=3)

    def __unicode__(self):
        return self.name

    #@models.permalink
    #def get_absolute_url(self):
    #    return ('location_template_view', [str(self.id)])

    class Meta:
        verbose_name = _("sequence")
        verbose_name = _("sequences")

    def get_next(self):
        # doing it *without* any lock!
        try:
            nnext = self.number_next
            self.number_next = self.number_next + 1
            num = ('%%s%%0%dd%%s' % self.padding) % (self.prefix or '', nnext, self.suffix or '')
            self.save()
            return num
        except Exception:
            # can we do anything here?
            raise

register(Location, _(u'locations'), ['name', 'address_line1', 'address_line2', 'address_line3', 'address_line4', 'phone_number1', 'phone_number2'])
register(Supplier, _(u'supplier'), ['name', 'address_line1', 'address_line2', 'address_line3', 'address_line4', 'phone_number1', 'phone_number2', 'notes'])


#eof
