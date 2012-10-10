# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save

class UserProfile(models.Model):
    # This field is required.
    user = models.OneToOneField(User)

    # Other fields here
    department = models.ForeignKey('company.Department', blank=True, null=True)

def create_user_profile(sender, instance, created, **kwargs):
    if created or not instance.get_profile():
        UserProfile.objects.create(user=instance)

# post_save.connect(create_user_profile, sender=User)
