from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib import messages

from models import DepartmentRole

def password_change_done(request):
    messages.success(request, _(u'Your password has been successfully changed.'))
    return redirect('home')

def select_user_role(request):
    role_id = request.GET.get('role_id', None)
    if role_id:
        role = get_object_or_404(DepartmentRole, pk=role_id)
        assert role.user == request.user, "User mismatch!"

        request.session['current_user_role'] = role.id

    return redirect('home')

#eof
