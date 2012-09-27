# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved
from django.utils.translation import ugettext_lazy as _
from common.api import register_links, register_menu
from common import supplier_list

register_menu([
    {'text':_('procurements'), 'view':'contract_list', 
            'links':[ {'text':_('delegates'), 'view':'delegate_list', 'famfam':'page_go'},
                {'text':_('projects'), 'view':'projects_list', 'famfam':'page_go'},
                {'text':_('contracts'), 'view':'contract_list', 'famfam':'page_go'},
                supplier_list,
                ],
        'famfam':'basket','position':3}]) # FIXME: icon

# register links?