# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved

from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from inventory.models import Inventory
import logging

class Command(BaseCommand):
    args = '<inventory_id ...>'
    help = 'Generates a PDF for the specified inventory'
    option_list = BaseCommand.option_list + (
        make_option('-o', '--output',
            default='inventory_.pdf',
            help='Output file to write to. Otherwize "inventory_xx.pdf"'),
        )

    def handle(self, *args, **options):
        from django.template.loader import render_to_string
        from rml2pdf import parseString
        fnamee = options['output'].rsplit('.', 1)
        logger = logging.getLogger('apps.inventory.commands')
        if not args:
            raise CommandError("Must supply an argument!")

        for inv_id in args:
            try:
                inventory = Inventory.objects.get(pk=int(inv_id))
                fname = '.'.join([fnamee[0] + inv_id] + fnamee[1:])
                logger.info("Rendering inventory #%d %s to \"%s\"", inventory.id, inventory.name, fname)

                rml_str = render_to_string('inventory_list.rml.tmpl',
                        dictionary={ 'object': inventory, 'report_name': fname,
                                'internal_title': "Inventory %d" % inventory.id,
                                'author': "Django-inventory"  } )
                out = parseString(rml_str, localcontext={}, fout=fname)
                # print out
            except Exception:
                logger.exception("Cannot render inventory %s", inv_id)


#eof
