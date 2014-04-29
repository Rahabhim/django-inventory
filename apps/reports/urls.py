# -*- encoding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from django.utils.translation import ugettext_lazy as _

urlpatterns = patterns('reports.views',
    url(r'^$', 'reports_app_view', (), name='reports_app_view'),
    )

#eof
