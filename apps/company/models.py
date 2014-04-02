# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist, ValidationError

import logging
logger = logging.getLogger('apps.'+__name__)

class DepartmentType(models.Model):
    name = models.CharField(max_length=128, verbose_name=_('name'))
    location_tmpl = models.ManyToManyField('common.LocationTemplate', blank=True, related_name='location_tmpl',
            through='DepartmentLocTemplates',
            verbose_name=_('location templates'),
            help_text=_(u"These will automatically be setup as locations, for each new department of this type") )

    class Meta:
        ordering = ['name']
        permissions = [('admin_company', 'Can manage companies'),]
        verbose_name = _("department type")

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('company_department_type_view', [str(self.id)])

class DepartmentLocTemplates(models.Model):
    dept_type = models.ForeignKey(DepartmentType, verbose_name=_('department type'))
    loc_tmpl = models.ForeignKey('common.LocationTemplate', verbose_name=_('location template'))
    nactive = models.IntegerField(verbose_name=_("number of active"), default=1)
    ncreate = models.IntegerField(verbose_name=_("total number to create"), default=1)

    class Meta:
        verbose_name = _("Assigned Template")
        verbose_name_plural = _("Assigned Templates")

    #def __unicode__(self):
    #    return self.

class Department(models.Model):
    name = models.CharField(max_length=128,verbose_name=_("name"))
    code = models.CharField(max_length=32, verbose_name=_("code"))
    code2 = models.CharField(max_length=32, blank=True, null=True, verbose_name=_("code 2"))
    deprecate = models.BooleanField(verbose_name=_("deprecated"))
    dept_type = models.ForeignKey(DepartmentType, verbose_name=_('Department Type'))
    merge = models.ForeignKey('Department', verbose_name=_('Merged in'), 
            related_name='dept_merge_id', blank=True, null=True, on_delete=models.PROTECT)
    nom_name = models.CharField(max_length=128, verbose_name=_('Nom Name'), blank=True, null=True)
    note = models.TextField(verbose_name=_('Note'), blank=True)
    ota_name = models.CharField(max_length=128, verbose_name=_('OTA Name'), blank=True, null=True)
    parent = models.ForeignKey('self', verbose_name=_('Parent Department'), related_name='dept_parent_id', blank=True, null=True, on_delete=models.PROTECT)
    section_name = models.CharField(max_length=128, verbose_name=_('Section'), blank=True, null=True)
    serviced_by = models.ForeignKey('self', verbose_name=_("Serviced By"),
           related_name='dept_service_id', blank=True, null=True)
    sequence = models.ForeignKey('common.Sequence', verbose_name=_("Sequence for items"), blank=True, null=True)

    class Meta:
        # admin = True
        ordering = ['name']
        permissions = [('admin_company', 'Can manage companies'),]
        verbose_name = _("department")
        verbose_name_plural = _("departments")

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('company_department_view', [str(self.id)])

    def clean(self):
        if self.parent and self.parent == self:
            raise ValidationError(_("The department cannot have itself as a parent"))
        return super(Department, self).clean()

    def get_sequence(self):
        if self.deprecate or self.merge:
            return ValueError("A deprecated or merged department cannot issue sequence IDs")
        if self.sequence:
            return self.sequence
        elif self.parent:
            assert self.parent != self, "Department \"%s\" is self-parented!" % self.name
            return self.parent.get_sequence()
        else:
            raise ObjectDoesNotExist(_("No sequence for department %s") % self.name)

    def fix_locations(self):
        """Update Locations for this Department, from template(s)
        """
        try:
            locs_by_tmpl = {}
            for loc in self.location_set.all():
                if loc.template is not None:
                    tmpl_id = loc.template.id
                    locs_by_tmpl[tmpl_id] = locs_by_tmpl.get(tmpl_id, 0) + 1
                    # We don't count active ones, we treat all existing as active, here

            for dtlt in self.dept_type.departmentloctemplates_set.all():
                lt = dtlt.loc_tmpl
                nold = locs_by_tmpl.get(lt.id, 0)
                while nold < dtlt.ncreate:
                    if nold or dtlt.ncreate > 1:
                        name = lt.name + (' %d' % (nold + 1))
                    else:
                        name = lt.name
                    self.location_set.create(name=name, sequence=lt.sequence,
                                usage='internal', template=lt,
                                active=(nold < dtlt.nactive))
                    nold += 1

        except ObjectDoesNotExist:
            pass

@receiver(post_save, sender=Department, dispatch_uid='139i436')
def post_save(sender, **kwargs):
    """ create the locations, after a department has been saved
    """
    if kwargs.get('created', False) and not kwargs.get('raw', False):
        assert kwargs.get('instance', None), 'keys: %r' % (kwargs.keys(),)
        dept = kwargs['instance']
        dept.fix_locations()

#eof
