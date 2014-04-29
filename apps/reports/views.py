# -*- encoding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

def reports_app_view(request, object_id=None):
    return render_to_response('reports_app.html',
            {},
            context_instance=RequestContext(request))

# eof