# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.db import models
from django.utils.translation import ugettext_lazy as _

class Partner(models.Model):
    name = models.CharField(max_length=128, unique=True)
    active = models.BooleanField(verbose_name=_("active"), default=False)
    web = models.CharField(max_length=128, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    # category = 

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Address(models.Model):
    name = models.CharField(max_length=128, verbose_name=_("contact"))
    partner = models.ForeignKey(Partner, db_index=True)
    address = models.TextField(blank=True, null=True)
    active = models.BooleanField(verbose_name=_("active"), default=False)
    phone1 = models.CharField(max_length=32, verbose_name=_("phone"), blank=True, null=True)
    phone2 = models.CharField(max_length=32, verbose_name=_("phone 2"), blank=True, null=True)


    def __unicode__(self):
        return self.name

#eof
