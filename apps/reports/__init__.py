# -*- encoding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from common.api import register_links, register_menu, can_add, can_edit

from models import SavedReport

report_create = {'text':_('create new report'), 'view':'reports_app_view',
        'famfam':'report_add', 'condition': can_add(SavedReport)}

report_edit = {'text': _('edit report'),
        'url_fn': lambda r: r.get_edit_url(), 'args': ['object'],
        'hide_text': True,
        'famfam': 'pencil', 'condition': can_edit}

register_links(['reports_list_view',], [report_create], menu_name='sidebar')
register_links(SavedReport, [report_edit])

register_menu([
    {'text':_('Reports'), 'view':'reports_list_view',
        'famfam':'report', 'position':20,
    },
])

#eof