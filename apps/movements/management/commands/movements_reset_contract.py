# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2014
# Only a few rights reserved

import logging
from company.management.commands.misc import verbosity_levels, SyncCommand, CommandError

from assets.models import Item
from common.models import Location

class Command(SyncCommand):
    help = 'Reset contract-id on assets, based on POs'

    def create_parser(self, prog_name, subcommand):
        parser = super(Command, self).create_parser(prog_name, subcommand)
        parser.add_option('--offset', type=int, help="Offset of items to process")
        return parser

    def handle(self, *args, **options):
        self._pre_handle(*args, **options)
        self._offset = int(options['offset'] or False)
        logger = logging.getLogger('command')


        qset = Item.objects.filter(movements__purchase_order__isnull=False,
                                   location__usage='internal',
                                   src_contract_id__isnull=True)
        
        logger.info("There are %d items with blank contract id", qset.count())
        
        question = "Item #%d %s is at %s, contract=%s fix?"
        for item in qset[self._offset or 0:self._limit or 1000000L]:
            move = item.movements.filter(location_src__usage__in=('procurement', 'supplier'),
                                         state='done',
                                         purchase_order__isnull=False).order_by('-date_act')[0]
            if not move.purchase_order.procurement:
                logger.error("Got move #%d %s, without purchase order!", move.id, move)
                continue
            if self.ask(question, item.id, item, item.location, move.purchase_order):
                item.src_contract = move.purchase_order.procurement
                item.save()
                logger.debug("Saved item #%d", item.id)
        return None


#eof