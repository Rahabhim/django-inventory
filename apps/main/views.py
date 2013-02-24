# -*- encoding: utf-8 -*-
from django.shortcuts import render_to_response
from django.template import RequestContext
import logging

def home(request):
    logger = logging.getLogger('permissions')
    try:
        user_profile = request.user.get_profile()
    except Exception, e:
        logger.warning("Cannot get profile:", exc_info=True)
        user_profile = None
    current_user_role = None
    try:
        if not request.user.is_superuser:
            user_roles = request.user.dept_roles.all()
            current_user_role = request.session.get('current_user_role', None)
            if (not current_user_role) and (user_roles.count() == 1):
                current_user_role = request.session['current_user_role'] = user_roles[0].role_id
                request.session.modified = True
        else:
            user_roles = []
    except Exception, e:
        logger.warning("Cannot prepare user role:", exc_info=True)
        user_roles = []

    return render_to_response('home.html', {'user_profile': user_profile, 
                    'user_roles': user_roles, 'current_user_role': current_user_role},
            context_instance=RequestContext(request))
