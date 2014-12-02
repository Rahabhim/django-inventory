# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012-2014
# Only a few rights reserved

from company.management.commands.misc import verbosity_levels, SyncCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
import logging

from common.models import Partner, Supplier
from products.models import Manufacturer, ItemTemplate
from procurements.models import Delegate, Contract

#from assets.models import Item
from movements.models import PurchaseOrder

class Command(SyncCommand):
    help = 'Merges partners (Suppliers, Manufacturers, Delegates)'
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

        target = Partner.objects.get(pk=int(args[0]))
        source_ids = map(int, args[1:])

        if target.id in source_ids:
            raise CommandError("Target id #%d is contained in source ids" % target.id)

        source_partners = Partner.objects.filter(id__in=source_ids)
        if not source_partners.exists():
            logger.warning("No source partners found")
            return

        print "Will merge these partners:"
        need_models = {}
        for src in source_partners:
            letters = ''
            for nmodel, letter in ('supplier', 'S'), ('manufacturer', 'M'), ('delegate', 'D'):
                try:
                    getattr(src, nmodel)
                    need_models[nmodel] = True
                    letters += ' +%s' % letter
                except ObjectDoesNotExist:
                    pass

            print "    #%5d %s%s" % (src.id, src.name, letters)
        print "\nInto this one:"
        print "    #%5d %s" % (target.id, target.name)

        if self.ask("Are you sure?"):

            cdict = target.__dict__.copy()
            for k in cdict.keys():
                if k == 'id' or k.startswith('_'):
                    cdict.pop(k)

            if need_models.get('supplier'):
                try:
                    supplier = target.supplier
                except ObjectDoesNotExist:
                    # create a new, preserving Partner fields
                    supplier = Supplier(partner_ptr_id=target.id)
                    supplier.__dict__.update(cdict)
                    supplier.save()

                PurchaseOrder.objects.filter(supplier_id__in=source_ids).update(supplier=supplier)
                for product in ItemTemplate.objects.filter(suppliers__in=source_ids):
                    # just add the new, partner deletion will remove the old one
                    product.suppliers.add(supplier)

            if need_models.get('delegate'):
                try:
                    delegate = target.delegate
                except ObjectDoesNotExist:
                    delegate = Delegate(partner_ptr_id=target.id)
                    delegate.__dict__.update(cdict)
                    delegate.save()
                Contract.objects.filter(delegate_id__in=source_ids).update(delegate=delegate)

            if need_models.get('manufacturer'):
                try:
                    manufacturer = target.manufacturer
                except ObjectDoesNotExist:
                    manufacturer = Manufacturer(partner_ptr_id=target.id)
                    manufacturer.__dict__.update(cdict)
                    manufacturer.save()
                ItemTemplate.objects.get(manufacturer_id__in=source_ids).update(manufacturer=manufacturer)

            logger.info("Partners %s merged into #%d", ', '.join(map(str, source_ids)), target.id)
            source_partners.delete()

        return

#eof
