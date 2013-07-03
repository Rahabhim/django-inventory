# -*- encoding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from models import HelpTopic

sub_topic_modes = {'app': [ ('model', _("Models")), ('view', _("Views"))],
            'model': [('field', _("Fields")),],
            }

def help_display_view(request, object_id):
    topic = get_object_or_404(HelpTopic, pk=object_id)
    user_can_edit = False
    if topic.active or request.user.is_staff:
        user_can_edit = True
    else:
        raise PermissionDenied

    sub_topics = []
    for smode, title in sub_topic_modes.get(topic.mode, []):
        sts = HelpTopic.objects.by_request(request)\
                    .filter(mode=smode, tkey__startswith=topic.tkey +'.')
        if sts.exists():
            sub_topics.append((title, sts))

    return render_to_response('help_topic_display.html',
            {'topic': topic, 'can_edit': user_can_edit, 'sub_topics': sub_topics },
            context_instance=RequestContext(request))

def help_index_view(request, key=None, mode=None):
    
    data = {'topics': HelpTopic.objects.by_request(request), 
                'key':key, 'mode': mode}
    
    if key is None:
        if mode is None:
            data['our_topics'] = data['topics'].filter(mode='app')
            data['other_topics'] = data['topics'].filter(mode='general')
    return render_to_response('help_index.html', data,
            context_instance=RequestContext(request))



"""
actions:
    create topic
    rescan models
   """
   

# eof