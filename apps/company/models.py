# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models
from django.utils.translation import ugettext_lazy as _

class DepartmentType(models.Model):
    name = models.CharField(max_length=128)

    class Meta:
        permissions = [('admin_company', 'Can manage companies'),]

class Department(models.Model):
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=32)
    code2 = models.CharField(max_length=32)
    deprecate = models.BooleanField()
    dept_type = models.ForeignKey(DepartmentType, verbose_name=_('Department Type'))
    merge = models.ForeignKey('Department', verbose_name=_('Merged in'), 
            related_name='dept_merge_id', blank=True, null=True)
    nom_name = models.CharField(max_length=128, verbose_name=_('Nom Name'), blank=True, null=True)
    note = models.TextField(verbose_name=_('Note'), blank=True)
    ota_name = models.CharField(max_length=128, verbose_name=_('OTA Name'), blank=True, null=True)
    parent = models.ForeignKey('Department', verbose_name=_('Parent Department'), related_name='dept_parent_id', blank=True, null=True)
    section_name = models.CharField(max_length=128, verbose_name=_('Section'), blank=True, null=True)

    class Meta:
        # admin = True
        permissions = [('admin_company', 'Can manage companies'),]

#eof
