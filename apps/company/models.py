# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist

class DepartmentType(models.Model):
    name = models.CharField(max_length=128)
    location_tmpl = models.ManyToManyField('common.LocationTemplate', blank=True, related_name='location_tmpl',
            help_text=_(u"These will automatically be setup as locations, for each new department of this type") )

    class Meta:
        permissions = [('admin_company', 'Can manage companies'),]

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('company_department_type_view', [str(self.id)])

class Department(models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32)
    code2 = models.CharField(max_length=32, blank=True, null=True)
    deprecate = models.BooleanField()
    dept_type = models.ForeignKey(DepartmentType, verbose_name=_('Department Type'))
    merge = models.ForeignKey('Department', verbose_name=_('Merged in'), 
            related_name='dept_merge_id', blank=True, null=True)
    nom_name = models.CharField(max_length=128, verbose_name=_('Nom Name'), blank=True, null=True)
    note = models.TextField(verbose_name=_('Note'), blank=True)
    ota_name = models.CharField(max_length=128, verbose_name=_('OTA Name'), blank=True, null=True)
    parent = models.ForeignKey('self', verbose_name=_('Parent Department'), related_name='dept_parent_id', blank=True, null=True)
    section_name = models.CharField(max_length=128, verbose_name=_('Section'), blank=True, null=True)
    serviced_by = models.ForeignKey('self', verbose_name=_("Serviced By"), 
           related_name='dept_service_id', blank=True, null=True)

    class Meta:
        # admin = True
        ordering = ['name']
        permissions = [('admin_company', 'Can manage companies'),]

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('company_department_view', [str(self.id)])

@receiver(post_save, sender=Department, dispatch_uid='139i436')
def post_save(sender, **kwargs):
    """ create the locations, after a department has been saved
    """
    from common.models import Location
    if kwargs.get('created', False) and not kwargs.get('raw', False):
        assert kwargs.get('instance', None), 'keys: %r' % (kwargs.keys(),)
        dept = kwargs['instance']
        try:
            for lt in dept.dept_type.location_tmpl.all():
                dept.location_set.create(name=lt.name, usage='internal')
        except ObjectDoesNotExist:
            pass

    # instance, created, raw, using=None)


#eof
