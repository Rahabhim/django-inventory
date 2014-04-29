# -*- encoding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from common.api import register_links, register_menu

register_menu([
    {'text':_('Reports'), 'view':'reports_app_view',
        'famfam':'report', 'position':20,
    },
])

#eof