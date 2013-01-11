# -*- encoding: utf-8 -*-
from django.shortcuts import render_to_response
from django.template import RequestContext

def home(request):
    try:
        user_profile = request.user.get_profile()
    except Exception, e:
        #print "exc:", e
        pass
    return render_to_response('home.html', {'user_profile': user_profile},
            context_instance=RequestContext(request))
