# -*- encoding: utf-8 -*-
from django import template
import logging
# from main import cart_utils
#from django.db import models
#import settings
from django.utils.translation import ugettext as _
from common.templatetags.navigation import resolve_to_name
from dhelp.models import HelpTopic

register = template.Library()
logger = logging.getLogger('dhelp.tags')

def _discover_view(context):
    if 'dhelp' in context:
        return
    
    current_path = template.Variable('request').resolve(context).META['PATH_INFO']
    current_view = resolve_to_name(current_path, prefix=True)

    try:
        object_name = template.Variable('navigation_object_name').resolve(context)
    except template.VariableDoesNotExist:
        object_name = 'object'

    try:
        obj = template.Variable(object_name).resolve(context)
    except template.VariableDoesNotExist:
        obj = None

    context['dhelp'] = {'view': current_view, 'obj': obj }

@register.simple_tag(takes_context=True)
def help_for_view(context):

    _discover_view(context)

    try:
        topic = HelpTopic.objects.get(tkey=context['dhelp']['view'], mode='view')
        edit_link = ''
        if context['request'].user.is_staff:
            edit_link = '<a href="/help/topic/%s/update/" class="famfam active famfam-pencil">%s</a>' % \
                    (topic.id, _("Edit"))
        if topic.content and topic.active:
            return '<div class="dhelp">%s%s</div>' % (topic.content, edit_link)
        elif edit_link:
            # give superuser a chance to write it
            return '<div class="dhelp dhelp-missing">%s</div>' % edit_link
    except HelpTopic.DoesNotExist:
        if context['request'].user.is_staff:
            return '<div class="dhelp dhelp-create"><a href="/help/topic/create/?tkey=%s&mode=%s" class="famfam active famfam-new">%s</a></div>' % \
                    (context['dhelp']['view'], 'view', _("Write help"))

    return ''

@register.inclusion_tag('inline_help.html', takes_context=True)
def help_for(context, mode='view', field=None, suffix=None, **kwargs):
    _discover_view(context)

    tkl = []
    if mode in ('model', 'field'):
        obj = context['dhelp'].get('obj',None)
        if obj:
            tkl.append(obj._meta.app_label)
            tkl.append(obj._meta.object_name)
    elif mode in ('view', 'view_field'):
        view = context['dhelp'].get('view', None)
        if view:
            tkl.append(view)

    if field:
        tkl.append(field)
    if suffix:
        tkl.append(suffix)
    tkey = '.'.join(tkl)
    edit_link = ''
    visible = False
    try:
        topic = HelpTopic.objects.get(tkey=tkey, mode=mode)
        if topic.content and topic.active:
            visible = True
        if context['request'].user.is_staff:
            visible = True
            edit_link = '/help/topic/%s/update/' % topic.id
    except HelpTopic.DoesNotExist:
        topic = None
        if context['request'].user.is_staff:
            visible = True
            edit_link = '/help/topic/create/?tkey=%s&mode=%s' %(tkey, mode)

    return dict(kwargs, topic=topic, mode=mode, tkey=tkey, 
                edit_link=edit_link, visible=visible)


#eof