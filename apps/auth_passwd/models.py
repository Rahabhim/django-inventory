# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.contrib.auth.models import User, Group
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

class UserProfile(models.Model):
    # This field is required.
    user = models.OneToOneField(User)

    # Other fields here
    department = models.ForeignKey('company.Department', blank=True, null=True)

class DepartmentRole(models.Model):
    user = models.ForeignKey(User, related_name="dept_roles") # required

    department = models.ForeignKey('company.Department', verbose_name=_("Department"))
    role = models.ForeignKey(Group, verbose_name=_("Group"))

    class Meta:
        unique_together = ('user', 'department') # Cannot have multiple roles for the same dept.

    def has_perm(self, perm):
        """Like User.has_perm(), see if role has that permission
        """
        # assume that the perm is like 'module.codename'
        app_label, codename = perm.split('.',1)
        return self.role.permissions.filter(content_type__app_label=app_label, \
                                            codename=codename).exists()

def create_user_profile(sender, instance, created, **kwargs):
    if created or not instance.get_profile():
        UserProfile.objects.create(user=instance)

# post_save.connect(create_user_profile, sender=User)
