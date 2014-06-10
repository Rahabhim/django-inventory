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

class Command(BaseCommand):
    args = ''
    help = 'Locates PO orders that have more items assigned than lines suggest'
    option_list = BaseCommand.option_list + \
        (   make_option('-o', '--offset',
                help='ID to compute from'),
            make_option('-l', '--limit',
                help="Number of POs to compute")
        )

    def handle(self, *args, **options):
        log = logging.getLogger('apps.movements.commands')

        pos = PurchaseOrder.objects.order_by('id')
        if args:
            pos = pos.filter(pk__in=map(int, args))
        elif options.get('offset'):
            print "offset:", options['offset']
            pos = pos.filter(pk__gt=int(options['offset']))

        if options.get('limit'):
            pos = pos[:int(options['limit'])]

        for po in pos:
            log.info("Processing purchase order: %d", po.id)
            try:
                mapped_items = po.map_items()
                all_ids = []
                for tdict in mapped_items.values():
                    for objs in tdict.values():
                        for o in objs:
                            if o.item_id:
                                all_ids.append(o.item_id)

                num_excess = 0
                for move in po.movements.all():
                    for it in move.items.all():
                        if it.id not in all_ids:
                            num_excess += 1

                if num_excess:
                    print "PO #%d %s has %d excess items" % (po.id, po, num_excess)

            except ValueError, ve:
                log.warning("Cannot map items: %s", ve)

#eof
