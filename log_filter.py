# -*- encoding: utf-8 -*-

from django.http import build_request_repr
from django.views.debug import SafeExceptionReporterFilter

class CookieSafeRF(SafeExceptionReporterFilter):
    _allowed_META_vars = ( 'HTTP_HOST', 'HTTP_ORIGIN', 'HTTP_PRAGMA', 'HTTP_REFERER',
                          'HTTP_USER_AGENT', 'PATH_INFO', 'PATH_TRANSLATED',
                          'QUERY_STRING', 'REMOTE_ADDR', 'REMOTE_PORT', 'REQUEST_METHOD',
                          'REQUEST_URI', 'SCRIPT_FILENAME', 'SCRIPT_NAME', 'SERVER_ADDR',
                          'SERVER_ADMIN', 'SERVER_NAME', 'SERVER_PORT')

    def get_post_parameters(self, request):
        params = super(CookieSafeRF, self).get_post_parameters(request)
        if params:
            if params is request.POST:
                params = params.copy()
            params.pop('csrfmiddlewaretoken', None)
        return params

    def get_request_repr(self, request):
        if request is None:
            return repr(None)
        else:
            return build_request_repr(request,
                                      POST_override=self.get_post_parameters(request),
                                      COOKIES_override={},
                                      META_override=self.get_meta_parameters(request))

    def get_meta_parameters(self, request):
        r = {}
        if request.META:
            for k, v in request.META.items():
                if k in self._allowed_META_vars:
                    r[k] = v
        if request.user is not None:
            try:
                r['user.id'] = request.user.id
                r['user'] = unicode(request.user)
            except Exception:
                pass
        return r


#eof
