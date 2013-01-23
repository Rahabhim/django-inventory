# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved
from django.utils.translation import ugettext_lazy as _
from common.api import register_links, register_menu, user_is_staff
from common import supplier_list

register_menu([
    {'text':_('procurements'), 'view':'purchase_order_list', 'id': 'menu_procurements',
            'links':[ {'text':_('delegates'), 'view':'delegate_list', 'famfam':'page_go',
                        'condition': user_is_staff },
                {'text':_('projects'), 'view':'projects_list', 'famfam':'page_go',
                        'condition': user_is_staff},
                {'text':_('contracts'), 'view':'contract_list', 'famfam':'page_go',
                        'condition': user_is_staff},
                supplier_list,
                ],
        'famfam':'basket','position':5}]) # FIXME: icon

# register links?