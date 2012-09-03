# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models
from django.utils.translation import ugettext_lazy as _

class DepartmentType(models.Model):
    name = models.CharField(max_length=128)

    class Meta:
        admin = True
        permissions = (('admin_company', 'Can manage companies'))
    #   _name = 'hr.department.type'
    #   _permissions = 'r'
    #   _search_filter = None

class Department(models.Model):
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=32)
    code2 = models.CharField(max_length=32)
    deprecate = models.BooleanField()
    dept_type_id = models.ForeignKey(DepartmentType, verbose_name=_('Department Type'))
    merge_id = models.ForeignKey('Department', verbose_name=_('Merged in'), related_name='dept_merge_id')
    nom_name = models.CharField(max_length=128, verbose_name=_('Nom Name'))
    note = models.TextField(verbose_name=_('Note'))
    ota_name = models.CharField(max_length=128, verbose_name=_('OTA Name'))
    parent_id = models.ForeignKey('Department', verbose_name=_('Parent Department'), related_name='dept_parent_id')
    section_name = models.CharField(max_length=128, verbose_name=_('Section'))

    class Meta:
        admin = True
        permissions = (('admin_company', 'Can manage companies'))


#eof
