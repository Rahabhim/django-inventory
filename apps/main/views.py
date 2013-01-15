# -*- encoding: utf-8 -*-
from django.shortcuts import render_to_response
from django.template import RequestContext

def home(request):
    try:
        user_profile = request.user.get_profile()
    except Exception, e:
        #print "exc:", e
        pass
    current_user_role = None
    try:
        if not request.user.is_superuser:
            user_roles = request.user.dept_roles.all()
            current_user_role = request.session.get('current_user_role', None)
        else:
            user_roles = []
    except Exception, e:
        # print "roles exc:", e
        user_roles = []

    return render_to_response('home.html', {'user_profile': user_profile, 
                    'user_roles': user_roles, 'current_user_role': current_user_role},
            context_instance=RequestContext(request))
