from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.utils import simplejson
from django.http import HttpResponse

from models import DepartmentRole

def password_change_done(request):
    messages.success(request, _(u'Your password has been successfully changed.'))
    return redirect('home')

def select_user_role(request):
    role_id = request.REQUEST.get('role_id', None)
    http_accept = request.META.get('HTTP_ACCEPT','-')
    if role_id:
        role = get_object_or_404(DepartmentRole, pk=role_id)
        assert role.user == request.user, "User mismatch!"

        request.session['current_user_role'] = role.id

    if request.is_ajax() and ('application/json' in http_accept):
        return_dict = {'success': True, 'data': role.id}
        json = simplejson.dumps(return_dict)
        return HttpResponse(json, mimetype="application/json")
    else:
        return redirect('home')

#eof
