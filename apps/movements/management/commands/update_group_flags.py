# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2014
# Only a few rights reserved

import logging
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option

from assets.models import ItemGroup

class Command(BaseCommand):
    args = ''
    help = 'Re-calculate state flags for Bundles'
    option_list = BaseCommand.option_list \
            +( make_option('-l', '--limit'),
              make_option('--offset'), )

    def handle(self, *args, **options):
        logger = logging.getLogger('command')
        offset = int(options.get('offset', 0) or 0)
        limit = int(options.get('limit', 0)) or None
        ItemGroup.objects.update_flags(location__usage='internal', offset=offset, limit=limit)
        
#eof