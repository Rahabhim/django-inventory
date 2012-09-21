from django.db import models
from django.utils.translation import ugettext_lazy as _
from dynamic_search.api import register

from common.models import Partner # , Supplier


class Delegate(Partner):
    """A delegate is a person or firm that performs procurements and maintainance, by contract
    
        In large organizations, supplies are not ordered on an item basis, but by mid-term
        procurement contracts. The contracts are `outsourced` to the delegates, which
        take on the administrative tasks.
    """
    #name = models.CharField(max_length=64)
    #parent = models.ForeignKey("ItemCategory", related_name="+", blank=True, null=True)
    code = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        # TODO: redundant
        ordering = ['name']
        
    @models.permalink
    def get_absolute_url(self):
        return ('delegate_view', [str(self.id)])

class Project(models.Model):
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
    
    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('project_view', [str(self.id)])

class Contract(models.Model):
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    date_start = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True) # called 'date' in oerp
    warranty_dur = models.CharField(max_length=64, blank=True, null=True)
    service_response = models.CharField(max_length=64, blank=True, null=True)
    repair_time = models.CharField(max_length=64, blank=True, null=True)
    kp_filename = models.CharField(max_length=128, blank=True, null=True)
    partner = models.ForeignKey(Partner, blank=True, null=True) # Either department or manager
    parent = models.ForeignKey(Project)
    delegate = models.ForeignKey(Delegate, related_name='delegate', blank=True, null=True)

    class Meta:
        ordering = ['name']
    
    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('contract_view', [str(self.id)])

#TODO: register..

#eof
