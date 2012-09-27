# -*- encoding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from main.conf import settings

import optparse
import logging
from main import mysql_suck as M

def custom_options(parser):
    M.MyS_Connector.add_mysql_options(parser)
    pgroup = optparse.OptionGroup(parser, "Iteration options")
    pgroup.add_option('--limit', type=int, help="Limit of forms to import"),
    pgroup.add_option('--dry-run', action="store_true", default=False,
                help="Don't change anything")
    pgroup.add_option('--slice', type=int,
                help="Slice of records to process at a time"),


class Command(BaseCommand):
    args = '<table ...>'
    help = 'Imports table from old Ktim. database'
    _myc = None
    _tables = []

    def create_parser(self, prog_name, subcommand):
        parser = super(Command, self).create_parser(prog_name, subcommand)
        custom_options(parser)
        return parser

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.DEBUG)
        self._init_tables()

        for d in settings.defaults:
            if options.get(d, None) is None:
                options[d] = settings.defaults[d]

        if not self._myc.connect(options, load=True):
            self.stderr.write("Cannot connect to MySQL!\n")
            return
        self.stderr.write("Connected. Start of sync\n")

        self._myc.run_all( args or ['KT_01_ANADOXOI',
                'KT_03_EIDOS',
                'KT_08_KATASKEYASTHS',
                'KT_05_PROIONTA',
                'KT_11_MANAGERS',
                'KT_16_ANATH_ARXH',
                'KT_18_ERGA',
                'KT_06_YPOERGA',
                'MONADES',
                ], **options)
        self._myc.close(save=True)
        return

    def _init_tables(self):
        self._myc = myc = M.MyS_Connector()
        
        anadoxoi = M.Table_Suck('KT_01_ANADOXOI', 'procurements.Delegate', myc)
        anadoxoi += M.IDmap_Column('ANADOXOS_ID')
        anadoxoi += M.Str_Column('ANADOXOS_DESCR', 'name')
        anadoxoi += M.Str_Column('WEB', 'web')
        anadoxoi_addr = M.Contain_Column('common.Address', 'partner')
        anadoxoi += anadoxoi_addr
        anadoxoi_addr += M.Str_Column('CONTACT_PERSON', 'name')
        anadoxoi_addr += M.Str_Column('TELEPHONE', 'phone1')
        anadoxoi_addr += M.Str_Column('CONTACT_TEL', 'phone2')

        # TODO KT_02_BUNDLES

        product_cat = M.Table_Suck('KT_03_EIDOS', 'products.ItemCategory', myc)
        product_cat += M.IDmap_Column('EIDOS_ID')
        product_cat += M.Str_Column('EIDOS_DESCR', 'name')
        # product_cat += M.Bool_Column('IS_BUNDLE', 'is_bundle')
        #product_cat += M.Static_Ref_Column(dict(parent_id=False),
        #        'parent_id', 'products.ItemCategory') TODO
        
        self._tables.append(product_cat)

#eof
