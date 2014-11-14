# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012-2014
# Only a few rights reserved

from company.management.commands.misc import verbosity_levels, SyncCommand, CommandError

import logging
from collections import namedtuple
from django.db.models import Q
from misc import verbosity_levels, ustr
import csv
from company.models import Department
from common.models import Sequence
from assets.models import Item

class Command(SyncCommand):
    help = 'Fix sequence generators for non-parented departments'
    logger = logging.getLogger('command')

    def create_parser(self, prog_name, subcommand):
        parser = super(Command, self).create_parser(prog_name, subcommand)
        parser.add_option('-S', '--sequence-id', type=int, help="Sequence to set at departments")
        return parser

    def handle(self, *args, **options):
        self._pre_handle(*args, **options)
        logger = logging.getLogger('command')

        depts = Department.objects.filter(parent__isnull=True, sequence__isnull=True)

        logger.info("We have %d Departments without parent nor sequence", depts.count())

        if depts and options['sequence_id']:
            seq = Sequence.objects.get(pk=int(options['sequence_id']))
            depts.update(sequence=seq)
            assets = Item.objects.filter(location__department__in=depts, property_number__isnull=True)
            if self.ask("Do update %d assets that have no property number ?", assets.count()):
                for a in assets.order_by('id'):
                    a.property_number = seq.get_next()
                    # in fact, save() would do the same, but we can bypass
                    # a few expensive location->department->sequence queries.
                    a.save()

        if self.ask("Look for parented departments with redundant sequence?"):
            depts = Department.objects.filter(parent__isnull=False, sequence__isnull=False)
            logger.info("Found %d departments with both a parent and sequence", depts.count())
            for dept in depts:
                try:
                    if dept.sequence == dept.parent.get_sequence() \
                            and self.ask("Parent #%d %s has same sequence %s as %s, remove?",
                                        dept.id, dept, dept.sequence, dept.parent):
                        dept.sequence = None
                        dept.save()
                except Sequence.DoesNotExist:
                    pass

        rest_assets = Item.objects.filter(location__department__isnull=False, property_number='')
        if self.ask("Fix remaining %d assets w/o property_number?", rest_assets.count()):
            for a in rest_assets.order_by('id'):
                a.save()

        return

#eof
