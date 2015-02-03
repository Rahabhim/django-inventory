# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models
from django.utils.translation import ugettext_lazy as _
from dynamic_search.api import register
from django.core.exceptions import ValidationError, ObjectDoesNotExist
import logging

class PartnerManager(models.Manager):
    def by_request(self, request):
        if request.user.is_superuser or request.user.is_staff:
            return self.all()
        else:
            return self.filter(active=True)

class Partner(models.Model):
    objects = PartnerManager()
    name = models.CharField(max_length=128, db_index=True, unique=True, verbose_name=_("name"))
    active = models.BooleanField(verbose_name=_("active"), default=False)
    web = models.CharField(max_length=128, blank=True, null=True)
    comment = models.TextField(blank=True, null=True, verbose_name=_("comment"))
    # category = 

    class Meta:
        ordering = ['name']
        verbose_name = _("partner")
        verbose_name_plural = _("partners")

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
    nactive = models.IntegerField(verbose_name=_("number of active"), default=1)
    ncreate = models.IntegerField(verbose_name=_("total number to create"), default=1)

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
    """ Place inside a Department, where assets can be stored/registered
    
        The usage is modelled after the OpenERP values.
        inventory is a virtual location, used to correct stock levels
    """
    name = models.CharField(max_length=32, verbose_name=_("name"), db_index=True)
    sequence = models.IntegerField(verbose_name=_("sequence"), default=10)
    department = models.ForeignKey('company.Department', null=True, blank=True, verbose_name=_("department"), on_delete=models.PROTECT)
    template = models.ForeignKey(LocationTemplate, verbose_name=_('From template'), null=True, blank=True)

    usage = models.CharField(max_length=32, verbose_name=_("location type"),
            choices=[('customer', _('Customer')), ('procurement', _('Procurement')), 
                    ('internal', _('Internal')), ('inventory', _('Inventory')), 
                    ('supplier', _('Supplier Location')), ('production', _('Bundled'))])
    active = models.BooleanField(default=True, verbose_name=_(u'active'))

    class Meta:
        ordering = ['sequence', 'name']
        verbose_name = _(u"location")
        verbose_name_plural = _(u"locations")
        permissions = ( ('locations_edit_active', 'Can activate or deactivate locations'), )

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
            from company.models import Department
            raise Department.DoesNotExist("No department for location %s" % self.name)

    def fmt_active(self):
        if self.active:
            return _(u'Active')
        else:
            return _(u'Inactive')

class Supplier(Partner):
    #TODO: Contact, extension
    objects = PartnerManager()
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
        verbose_name_plural = _("sequences")

    def get_next(self):
        this = Sequence.objects.select_for_update().get(pk=self.id)
        try:
            nnext = this.number_next
            this.number_next = this.number_next + 1
            num = ('%%s%%0%dd%%s' % self.padding) % (self.prefix or '', nnext, self.suffix or '')
            this.save()
            return num
        except Exception, e:
            # can we do anything here?
            logging.getLogger('apps.common.sequence') \
                    .error("Cannot get sequence %d number: %s", self.id, e)
            raise

register(Location, _(u'locations'), ['name', 'address_line1', 'address_line2', 'address_line3', 'address_line4', 'phone_number1', 'phone_number2'])
register(Supplier, _(u'supplier'), ['name', 'address_line1', 'address_line2', 'address_line3', 'address_line4', 'phone_number1', 'phone_number2', 'notes'])


#eof
