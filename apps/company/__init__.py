# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved
from django.utils.translation import ugettext_lazy as _
from common.api import register_links, register_menu
from common import location_list

register_menu([
    {'text':_('company'), 'view':'company_department_list', 
            'links':[ {'text':_('departments'), 'view':'company_department_list', 'famfam':'page_go'},
                {'text':_('department types'), 'view':'company_department_type_list', 'famfam':'page_go'},
                location_list,
                ],
        'famfam':'building','position':4}])

#eof