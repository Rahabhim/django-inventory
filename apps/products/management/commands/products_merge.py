# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012-2014
# Only a few rights reserved

from company.management.commands.misc import verbosity_levels, SyncCommand, CommandError

import logging

from products.models import ItemTemplate
from assets.models import Item
from movements.models import PurchaseOrderItem, PurchaseOrderBundledItem, PurchaseRequestItem

class Command(SyncCommand):
    help = 'Merges multiple products into a single one'
    args = '[--interactive] <target-id> <source-id> ...'
    logger = logging.getLogger('command')

    #def create_parser(self, prog_name, subcommand):
    #    parser = super(Command, self).create_parser(prog_name, subcommand)
    #    parser.add_option('-S', '--sequence-id', type=int, help="Sequence to set at departments")
    #    return parser

    def handle(self, *args, **options):
        self._pre_handle(*args, **options)
        logger = logging.getLogger('command')

        if len(args) < 2:
            raise CommandError("Must give at least 2x IDs to merge")

        target = ItemTemplate.objects.get(pk=int(args[0]))
        source_ids = map(int, args[1:])

        if target.id in source_ids:
            raise CommandError("Target id #%d is contained in source ids" % target.id)

        source_products = ItemTemplate.objects.filter(id__in=source_ids)
        if not source_products.exists():
            logger.warning("No source products found")
            return

        iz_ok = True
        for src in source_products:
            if src.category != target.category:
                logger.error("Category for #%d %s is %s", src.id, src.description, src.category)
                iz_ok = False
            if src.manufacturer != target.manufacturer:
                logger.error("Manufacturer for #%d %s is %s", src.id, src.description, src.manufacturer)
                iz_ok = False

        if not iz_ok:
            raise CommandError("Products don't match, cannot merge")
        print "Will merge these products:"
        for src in source_products:
            print "    #%5d %s" % (src.id, src.description)
        print "\nInto this one:"
        print "    #%5d %s" % (target.id, target.description)

        if self.ask("Are you sure?"):
            Item.objects.filter(item_template__in=source_products).update(item_template=target)
            PurchaseRequestItem.objects.filter(item_template__in=source_products).update(item_template=target)
            PurchaseOrderItem.objects.filter(item_template__in=source_products).update(item_template=target)
            PurchaseOrderBundledItem.objects.filter(item_template__in=source_products).update(item_template=target)
            logger.info("Products %s merged into #%d", ', '.join(map(str, source_ids)), target.id)

            source_products.delete()
        return

#eof
