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
                help="Number of POs to compute"),
            make_option('-d', '--detail', action="store_true", default=False,
                help="List excess items, in detail"),
            make_option('--delete', action="store_true", default=False,
                help="Delete excess items. DANGEROUS! Will only work if explicit list of PO IDs is given as arguments"),
        )

    def _print_detail(self, po, excess_items, mapped_items=False, do_items=True):
        for poi in po.items.all():
            print "    %s x%d" %(poi, poi.qty)
            for boi in poi.bundled_items.all():
                print "        %s x%d" % (boi, boi.qty)
        if excess_items:
            print "Excess items:"
            for ei in excess_items:
                print "    %s #%d" % (ei, ei.id)

        if mapped_items:
            print "Missing items:"
            for tdict in mapped_items.values():
                for it_id, objs in tdict.items():
                    for o in objs:
                        if not o.item_id:
                            print "    - %s     %s" % (it_id, o.serial)

    def handle(self, *args, **options):
        log = logging.getLogger('apps.movements.commands')

        do_delete = False
        pos = PurchaseOrder.objects.order_by('id')
        if args:
            pos = pos.filter(pk__in=map(int, args))
            if options.get('delete'):
                do_delete = True
        elif options.get('offset'):
            pos = pos.filter(pk__gt=int(options['offset']))

        if options.get('limit'):
            pos = pos[:int(options['limit'])]

        if options['detail']:
            print_detail = self._print_detail
        else:
            print_detail = lambda *a, **k: None

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
                excess_items = []
                for move in po.movements.all():
                    for it in move.items.all():
                        if it.id not in all_ids:
                            num_excess += 1
                            excess_items.append(it)

                    if num_excess and move.checkpoint_dest is not None:
                        log.error("PO #%d has excess items, but move #%d is validated in %s",
                                po.id, move.id, move.checkpoint_dest)
                        print_detail(po, excess_items)
                        excess_items = None
                        num_excess = 0
                        break
                if num_excess and po.map_has_left(mapped_items):
                    log.warning("PO #%d has excess items, but is also missing some, not wise to modify", po.id)
                    print_detail(po, excess_items, mapped_items)
                    excess_items = None
                    continue

                if num_excess:
                    print "PO #%d %s has %d excess items" % (po.id, po, num_excess)
                    print_detail(po, excess_items)
                    if do_delete and excess_items:
                        for it in excess_items:
                            it.delete()
                        print "Excess items DELETED!"

            except ValueError, ve:
                log.warning("Cannot map items for PO %#d: %s", po.id, ve)

#eof
