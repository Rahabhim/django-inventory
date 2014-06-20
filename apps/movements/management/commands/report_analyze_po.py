# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2014
# Only some little rights reserved

import settings
from django.db import models
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from django.utils.translation import ugettext_lazy as _
import logging
from django.core.urlresolvers import RegexURLResolver, RegexURLPattern

from movements.models import PurchaseOrder
from products.models import ItemTemplate

class Command(BaseCommand):
    args = ''
    help = 'Analyzes items in PO order'
    option_list = BaseCommand.option_list

    def handle(self, *args, **options):
        log = logging.getLogger('apps.movements.commands')

        do_delete = False
        pos = PurchaseOrder.objects.order_by('id')
        if args:
            pos = pos.filter(pk__in=map(int, args))
        else:
            log.error("you must give some IDs to search for")
            return False

        for po in pos:
            log.info("Analyzing purchase order: %d", po.id)
            try:
                mapped_items = po.map_items()
                all_ids = []
                all_serials = []
                for loc_kind, tdict in mapped_items.items():
                    print "Location:", loc_kind or '*'
                    for product, objs in tdict.items():
                        try:
                            itt = ItemTemplate.objects.get(pk=product)
                            print "    product: %s" % itt
                        except ItemTemplate.DoesNotExist:
                            print "    product: #%d (not found!)" % product

                        for o in objs:
                            s = ''
                            if o.serial and o.serial in all_serials:
                                s = '* Dup serial!'
                            print "        %r %s" % (o, s)
                            if o.serial:
                                all_serials.append(o.serial)
                            #if o.item_id:
                            #    all_ids.append(o.item_id)

            except ValueError, ve:
                log.warning("Cannot map items for PO %#d: %s", po.id, ve)

#eof
