# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2014
# Only a few rights reserved

import logging
from company.management.commands.misc import verbosity_levels, SyncCommand, CommandError

from assets.models import Item
from common.models import Location
from datetime import timedelta
from django.db import transaction

class Command(SyncCommand):
    help = 'Verify/analyze Item movements with their location'

    def create_parser(self, prog_name, subcommand):
        parser = super(Command, self).create_parser(prog_name, subcommand)
        parser.add_option('--offset', type=int, help="Offset of items to process")
        parser.add_option('--long-verify', action="store_true", default=False,
                          help="Perform the long part, checking each movement")
        return parser

    def handle(self, *args, **options):
        self._pre_handle(*args, **options)
        self._offset = int(options['offset'] or False)
        logger = logging.getLogger('command')

        base_qset = Item.objects
        if args:
            base_qset = base_qset.filter(id__in=map(int, args))
        
        # First set: items never moved, never placed in location
        qset = base_qset.filter(movements__isnull=True, location__isnull=True)
        logger.debug("Searching Items w/o movements or location")
        if qset.exists() \
                and self.ask("There are %d items with no movements, no location. Delete?", qset.count()):
            qset.delete()

        qset = base_qset.filter(movements__isnull=True, location__isnull=False)
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

        qset = base_qset.filter(movements__isnull=False, location__isnull=True)
        qset2 = qset.filter(movements__state='done')
        if qset2.exists() \
                and self.ask("Process %d items that have movements but NO location?", qset2.count()):
            self.process_items(qset2)

        logger.debug("Searching Items with movements and location")
        qset = base_qset.filter(movements__isnull=False, location__isnull=False)
        if options['long_verify'] \
                or self.ask("Process rest of Items (%d), verify movements?", qset.count()):
            self.process_items(qset)

    @transaction.commit_manually
    def process_items(self, qset):
        try:
            self._process_items(qset)
            transaction.commit()
        except Exception:
            transaction.rollback()
            raise
        except KeyboardInterrupt:
            transaction.rollback()
            raise

    def _process_items(self, qset):
        """Verify that each item in `qset` has movements leading up to its current location
        """
        logger = logging.getLogger('command')
        qset2 = qset.order_by('id')
        if self._offset:
            qset2 = qset2[self._offset:]
        if self._limit:
            qset2 = qset2[:self._limit]

        def items_iter():
            all_ids = qset2.values_list('id', flat=True)
            qcount = len(all_ids)
            num = 0
            while all_ids:
                cur_ids = all_ids[:1000]
                all_ids = all_ids[1000:]
                num += len(cur_ids)
                for item in qset.filter(id__in=cur_ids).select_for_update():
                    yield item
                logger.info("Processed %d/%d items", num, qcount)
                transaction.commit()

        real_num = 0
        for item in items_iter():
            last_location = None
            last_movement = False
            cannot_reorder = False
            real_num += 1
            move_stack = list(item.movements.filter(state='done').order_by('date_act', 'id'))
            moves_to_save = []
            while move_stack:
                move = move_stack.pop(0)
                if move.state != 'done':
                    logger.warning("Move #%d in state %s returned by filter", move.id, move.state)
                    continue
                if (not last_location) and move.location_src.usage in ('procurement', 'supplier'):
                    pass
                elif move.location_src == last_location:
                    pass
                else:
                    for i, next_move in enumerate(move_stack):
                        if ((not last_location) and next_move.location_src.usage in ('procurement', 'supplier')) \
                                or (next_move.location_src == last_location):
                            next_date = next_move.date_act
                            if move.id < next_move.id:
                                next_date += timedelta(days=1)
                            if next_date > move.date_val:
                                logger.info("Cannot reorder move #%d after date=%s , because movement was validated at %s", move.id, next_date, move.date_val)
                                cannot_reorder = True
                                continue
                            if move.checkpoint_dest and move.checkpoint_dest.date_act < next_date:
                                logger.info("Cannot reorder move #%d after date=%s , because movement was checkpointed at %s", move.id, next_date, move.checkpoint_dest.date_val)
                                cannot_reorder = True
                                continue
                            if move.items.count() > 1:
                                logger.info("Cannot reorder move #%d because it contains more items (%d)", move.id, move.items.count())
                                cannot_reorder = True
                                continue
                            
                            # fix, move this "move" after "next_move". But don't save yet
                            move.date_act = next_date
                            moves_to_save.append(move)
                            move_stack.insert(i+1, move)
                            break
                    else:
                        try:
                            logger.error("Inconsistency! Item #%d %s was jumped locations from %s to %s, among movements:\n\t%s\n\t%s",
                                    item.id, item, last_location, move.location_src, last_movement or '(start)', move)
                        except UnicodeDecodeError:
                            # don't let logging errors break the loop
                            pass
                    # skip this move, continue with next ones in stack
                    continue

                last_location = move.location_dest
                last_movement = move
            
            if moves_to_save:
                if last_location == item.location:
                    result = "(locations ok)"
                else:
                    result = "(location mismatch)"
                for smove in moves_to_save:
                    if self.ask("Re-order movement #%d %s to date %s? "+ result , smove.id, unicode(smove), smove.date_act):
                        smove.save()
                    else:
                        cannot_reorder = True

            if last_location != item.location and not cannot_reorder:
                move_str = ''
                if last_movement:
                    # movement.id is part of the static question, other details aren't
                    move_str = " (move: #%d)" % last_movement.id
                question = "Item #%d %s should be at %s" + move_str + " but is now at %s, fix?"

                try:
                    if self.ask(question, item.id, item, last_location, item.location):
                        item.location = last_location
                        item.save()
                except UnicodeDecodeError:
                    pass
        logger.info("End, processed %d items", real_num)
        return None


#eof