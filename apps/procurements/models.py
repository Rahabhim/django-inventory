# -*- encoding: utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _
# from dynamic_search.api import register

from common.models import Partner, PartnerManager # , Supplier


class Delegate(Partner):
    """A delegate is a person or firm that performs procurements and maintainance, by contract
    
        In large organizations, supplies are not ordered on an item basis, but by mid-term
        procurement contracts. The contracts are `outsourced` to the delegates, which
        take on the administrative tasks.
    """
    objects = PartnerManager()
    #name = models.CharField(max_length=64)
    #parent = models.ForeignKey("ItemCategory", related_name="+", blank=True, null=True)
    code = models.CharField(max_length=32, blank=True, null=True, verbose_name=_("code"))

    class Meta:
        # TODO: redundant
        ordering = ['name']
        
    @models.permalink
    def get_absolute_url(self):
        return ('delegate_view', [str(self.id)])

class Project(models.Model):
    name = models.CharField(max_length=128, verbose_name=_("name"))
    description = models.TextField(blank=True, verbose_name=_("description"))

    class Meta:
        ordering = ['name']
    
    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('project_view', [str(self.id)])

class Contract(models.Model):
    name = models.CharField(max_length=128, verbose_name=_("name"))
    description = models.TextField(blank=True, verbose_name=_("description"))
    use_regular = models.BooleanField(default=True, verbose_name=_(u'use for regular procurements'))
    use_mass = models.BooleanField(default=False, verbose_name=_(u'use for mass procurements'))
    date_start = models.DateField(blank=True, null=True, verbose_name=_("start date"))
    end_date = models.DateField(blank=True, null=True, verbose_name=_("end date")) # called 'date' in oerp
    warranty_dur = models.CharField(max_length=64, blank=True, null=True, verbose_name=_("warranty duration"))
    service_response = models.CharField(max_length=64, blank=True, null=True, verbose_name=_("service response"))
    repair_time = models.CharField(max_length=64, blank=True, null=True, verbose_name=_("repair time"))
    kp_filename = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("filename"))
    department = models.ForeignKey('company.Department', blank=True, null=True, verbose_name=_("department")) # Either department or manager
    parent = models.ForeignKey(Project, verbose_name=_("project"))
    delegate = models.ForeignKey(Delegate, related_name='delegate', blank=True, null=True, verbose_name=_("delegete"))

    class Meta:
        ordering = ['name']
    
    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('contract_view', [str(self.id)])

#TODO: register..

#eof
