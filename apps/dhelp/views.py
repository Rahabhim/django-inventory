# -*- encoding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from models import HelpTopic

def help_display_view(request, object_id):
    topic = get_object_or_404(HelpTopic, pk=object_id)
    user_can_edit = False
    if topic.active or request.user.is_staff:
        user_can_edit = True
    else:
        raise PermissionDenied

    return render_to_response('help_topic_display.html',
            {'topic': topic, 'can_edit': user_can_edit },
            context_instance=RequestContext(request))

def help_index_view(request, key=None, mode=None):
    
    return render_to_response('help_index.html',
            {'topics': HelpTopic.objects.by_request(request), 
                'key':key, 'mode': mode},
            context_instance=RequestContext(request))



"""
actions:
    create topic
    rescan models
   """
   

# eof