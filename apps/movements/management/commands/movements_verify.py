# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2014
# Only a few rights reserved

import logging
from company.management.commands.misc import verbosity_levels, SyncCommand, CommandError

from assets.models import Item
from common.models import Location

class Command(SyncCommand):
    help = 'Verify/analyze Item movements with their location'

    def create_parser(self, prog_name, subcommand):
        parser = super(Command, self).create_parser(prog_name, subcommand)
        parser.add_option('--offset', type=int, help="Offset of items to process")
        return parser

    def handle(self, *args, **options):
        self._pre_handle(*args, **options)
        self._offset = int(options['offset'] or False)
        logger = logging.getLogger('command')

        # First set: items never moved, never placed in location
        qset = Item.objects.filter(movements__isnull=True, location__isnull=True)
        logger.debug("Searching Items w/o movements or location")
        if qset.exists() \
                and self.ask("There are %d items with no movements, no location. Delete?", qset.count()):
            qset.delete()

        qset = Item.objects.filter(movements__isnull=True, location__isnull=False)
        logger.debug("Searching Items w/o movements but set location")
        qset2 = qset.filter(location__usage__in=('procurement', 'supplier'))
        if qset2.exists():
            if self.ask("There are %d items w/o movements, location incoming. Clear?", qset2.count()):
                qset2.delete()

        qset2 = qset.exclude(location__usage__in=('procurement', 'supplier'))
        if qset2.exists():
            logger.info("Processing %d items that have a location but no movements:", qset2.count())
            for item in qset2.all():
                # we only set location.usage in the question string, other fields will
                # be variable w/o asking again.
                if self.ask("Item %%s is at %s location: %%s but never moved there. Delete?" \
                        % item.location.usage, item, item.location):
                    item.delete()

        qset = Item.objects.filter(movements__isnull=False, location__isnull=True)
        qset2 = qset.filter(movements__state='done')
        if qset2.exists() \
                and self.ask("Process %d items that have movements but NO location?", qset2.count()):
            self.process_items(qset2)

        logger.debug("Searching Items with movements and location")
        qset = Item.objects.filter(movements__isnull=False, location__isnull=False)
        if self.ask("Process rest of Items (%d), verify movements?", qset.count()):
            self.process_items(qset)

    def process_items(self, qset):
        """Verify that each item in `qset` has movements leading up to its current location
        """
        logger = logging.getLogger('command')
        qset2 = qset.order_by('id')
        if self._offset:
            qset2 = qset2[self._offset:]
        if self._limit:
            qset2 = qset2[:self._limit]

        num = 0
        qcount = qset2.count()
        for item in qset2.all():
            last_location = None
            last_movement = False
            num += 1
            if num % 1000 == 0:
                logger.info("Processed %d/%d items", num, qcount)
            for move in item.movements.filter(state='done').order_by('date_act'):
                if (not last_location) and move.location_src.usage in ('procurement', 'supplier'):
                    pass
                elif move.location_src == last_location:
                    pass
                else:
                    logger.error("Inconsistency! Item #%d %s was jumped locations from %s to %s, among movements:\n\t%s\n\t%s",
                            item.id, item, last_location, move.location_src, last_movement, move)

                last_location = move.location_dest
                last_movement = move

            if last_location != item.location:
                move_str = ''
                if last_movement:
                    # movement.id is part of the static question, other details aren't
                    move_str = " (move: #%d)" % last_movement.id
                question = "Item #%d %s should be at %s" + move_str + " but is now at %s, fix?"

                if self.ask(question, item.id, item, last_location, item.location):
                    item.location = last_location
                    item.save()
        return None


#eof