# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012-2014
# Only a few rights reserved

from django.core.management.base import BaseCommand, CommandError
import logging
from collections import namedtuple
from django.db.models import Q
from misc import verbosity_levels, ustr
import csv
from company.models import Department

class Command(BaseCommand):
    help = 'Restore GLUC codes from CSV'
    _named_cols = {'AA': 'code_mm', 'ONOMA_MON': 'name', 'GLUC': 'code2', 'YPEPTH_ID': 'code'}
    logger = logging.getLogger('command')

    def create_parser(self, prog_name, subcommand):
        parser = super(Command, self).create_parser(prog_name, subcommand)
        parser.add_option('-l', '--limit', type=int, help="Limit of users to process"),
        return parser

    def handle(self, *args, **options):

        v = options.get('verbosity', None)
        if v:
            vlevel = verbosity_levels.get(int(v), logging.INFO)
            self.logger.setLevel(vlevel)
            logging.getLogger().setLevel(vlevel)

        if len(args) != 1:
            raise CommandError("you must specify the CSV file as a single argument")
        
        fp = None
        limit = int(options.get('limit', None) or 0)
        try:
            fp = open(args[0], 'rb')
            reader = csv.reader(fp)
            col_names = []
            for nb, col in enumerate(map(ustr, reader.next())):
                col_names.append(self._named_cols.get(col,'col_%02d' % nb))
            DeptRow = namedtuple('dept_row', col_names)
            del col_names
        except Exception:
            self.logger.exception("Could not read file")
            raise CommandError("could not read file")
        
        self.num_q = self.num_ok = self.num_w = 0

        try:
            n = 0
            for rawline in reader:
                row = DeptRow._make(map(ustr, map(str.strip, rawline)))
                self.parseRow(row)
                if limit and n >= limit:
                    break
                n += 1
        except Exception:
            self.logger.exception("Cannot parse:")

        self.logger.info("In %d rows, %d queried, %d updated and %d passed", n, self.num_q, self.num_w, self.num_ok)
        fp.close()
        return None

    def parseRow(self, row):
        if not row.code:
            self.logger.debug("No code at: %s", row.name)
            return

        flt = Q(code=row.code)
        if row.code2:
            flt |= Q(code2=row.code2)
        #if row.code_mm:
            #flt |= Q(code_mm=row.code_mm)
        self.num_q += 1
        for dept in Department.objects.filter(flt):
            if dept.name != row.name.strip():
                self.logger.debug("Name mismatch: '%s' != '%s'", row.name, dept.name)
                continue
            if row.code2 == row.code:
                # code2 has been reset to code, original data lost
                pass
            elif row.code2 and (dept.code2 != row.code2):
                self.logger.info("Fixing code2 for %s: %r -> '%s'", row.name, dept.code2, row.code2)
                dept.code2 = row.code2
                dept.save()
                self.num_w += 1
            elif row.code != dept.code:
                self.logger.info("Fixing code for %s: %s", row.name, row.code)
                dept.code = row.code
                dept.save()
                self.num_w += 1
            else:
                self.num_ok += 1
            break
        else:
            self.logger.info("No department found for code=%s gluc=%s", row.code, row.code2)
            return False

        return True

#eof
