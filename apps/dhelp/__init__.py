# -*- encoding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from models import HelpTopic

from common.api import register_links, register_menu, _context_has_perm, \
        can_add, can_edit, can_delete, user_is_staff
        
help_topic_list = {'text':_('view all help topics'), 'view':'help_topic_list',
        'famfam':'help', 'condition': user_is_staff}
help_topic_create = {'text':_('create new help topic'), 'view':'help_topic_create',
        'famfam':'page_add', 'condition': can_add(HelpTopic)}
help_topic_update = {'text':_(u'edit'), 'view':'help_topic_update', 'args':'object.id',
        'famfam':'page_edit', 'condition': can_edit }
help_topic_delete = {'text':_(u'delete'), 'view':'help_topic_delete', 'args':'object.id',
        'famfam':'page_delete', 'condition': can_delete }

help_topic_view = {'text':_(u'view'), 'view':'help_display_view', 'args':'object.id',
        'famfam':'help'}

help_topic_index = {'text':_(u'index'), 'view':'help_index_view', 'famfam':'help' }

register_links(['help_topic_list',], [help_topic_create], menu_name='sidebar')

register_links(['help_topic_update', 'help_topic_view'], [help_topic_delete, ], menu_name='sidebar')

def has_pending_help(obj, context):
    return HelpTopic.objects.filter(active=False).exists()

action_help_pending = {'text':_('pending help topics'), \
        'condition': (user_is_staff, has_pending_help),
        'view': 'help_pending_list', 'famfam':'page_go'}


register_links(['home',], [action_help_pending ], menu_name='my_pending')

register_menu([
    {'text':_('Help'), 'view':'help_index_view', 
        'links': [ help_topic_index, help_topic_list, ],
        'famfam':'help', 'position':10,
        'condition': user_is_staff
        },
])

#eof