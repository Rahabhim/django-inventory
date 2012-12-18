# -*- encoding: utf-8 -*-
from company.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
import csv, codecs

import optparse
import logging

from misc import SyncCommand, CommandError

from company.models import Department

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    # Taken from Python documentation

    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

    def __getattr__(self, name):
        return getattr(self.reader, name)

class Command(SyncCommand):
    args = '<input file>'
    help = 'Imports a table of Departments'

    def create_parser(self, prog_name, subcommand):
        parser = super(Command, self).create_parser(prog_name, subcommand)
        parser.add_option('--encoding', help="Encoding to use")
        parser.add_option('--offset', type=int, help="Skip that many lines from the CSV")
        return parser

    def handle(self, *args, **options):
        for d, v in settings.csv_defaults.items():
            if options.get(d, None) is None:
                options[d] = v

        self._pre_handle(*args, **options)

        kws = {}
        for opt in ('encoding', 'delimiter'):
            if opt in options:
                kws[opt] = options[opt]

        if len(args) != 1:
            raise CommandError("Must give one input file!")

        logger = self._logger
        logger.info("Importing \"%s\" as CSV", args[0])

        try:
            fp = open(args[0], 'rb')
            reader = UnicodeReader(fp, **kws)
            cols = reader.next()
            logger.info("Columns: %r", cols)
            if options.get('offset', None):
                offset = options['offset']
                for line in reader:
                    offset -= 1
                    if offset <= 0:
                        break
        except Exception:
            logger.exception("Could not parse file: ")

    def _import_departments(self, reader, cols):
        logger = self._logger
        if True:
            num_done = 0
            known_depts = []
            for line in reader:
                if num_done >= self._limit:
                    break
                res = dict(zip(cols, line))
                logger.debug("Doing #%s (fy: %s) : %s", res.get('YPEPTH_ID', '--'), res.get('FY_ID',''), res.get('ONOMA_MON', '?'))
                num_done += 1
                if not res.get('YPEPTH_ID',False):
                    logger.warning(u"Η μονάδα: %s δεν έχει ypepth_id (γραμμή %d), την περνάμε", \
                            res.get('ONOMA_MON', '?'), reader.line_num)
                    continue

                dres = Department.objects.filter(Q(code=res['YPEPTH_ID'])|Q(code2=res['YPEPTH_ID']))
                if not dres:
                    logger.info(u"Η μονάδα %s δεν υπάρχει στη βάση: %s", res['YPEPTH_ID'], res['ONOMA_MON'])
                    dres = Department.objects.filter(name=res['ONOMA_MON'])
                    if dres and len(dres) > 1:
                        logger.warning(u"Βρέθηκαν %d μονάδες με το ίδιο όνομα: %s",
                                len(dres), res['ONOMA_MON'])
                        for d in dres:
                            logger.info(u"    #%d %s [%s]", d.id, d.code, d.code2, )
                        continue
                    elif dres:
                        d = dres[0]
                        logger.info(u"Βρέθηκε όμως η #%d %s [%s] με το ίδιο όνομα: %s",
                                d.id, d.code, d.code2, d.name)
                        if self.ask(u"Να αλλάξει ο κωδικός σε %s;", res['YPEPTH_ID']):
                            if not d.code2:
                                d.code2 = d.code # save the old one there
                            d.code = res['YPEPTH_ID']
                            d.save()
                            known_depts.append(d.id)
                elif len(dres) == 1:
                    d = dres[0]
                    logger.debug("Βρέθηκε το id=%d στη βάση με ίδιο κωδ.", d.id)

                    if res['YPEPTH_ID'] == d.code2 and self._active is not False:
                        # swap them.
                        d.code2 = d.code
                        d.code = res['YPEPTH_ID']
                        d.save()
                    if res.get('ONOMA_MON', '').strip() and d.name != res['ONOMA_MON']:
                        logger.info(u"Η μονάδα #%d \"%s\" πρέπει να μετονομαστεί σε \"%s\"",
                                d.id, d.name, res['ONOMA_MON'])
                        if self.ask(u"Να ενημερωθεί το όνομα;"):
                            d.name = res['ONOMA_MON']
                            d.save()
                            known_depts.append(d.id)
                    else:
                        known_depts.append(d.id)
                else:
                    logger.warning(u"Η μονάδα με κωδ.: %s υπάρχει %d φορές στη βάση:", \
                            res['YPEPTH_ID'], len(dres))
                    for d in dres:
                        logger.warning("    #%d %s [%s] %s", d.id, d.code, d.code2, d.name)
                    # TODO: what now?
                    continue
            else:
                logger.debug("limit not reached!")
                logger.debug("Known depts: %d", len(known_depts))

#eof
