# -*- encoding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from django.utils.translation import ugettext_lazy as _

urlpatterns = patterns('reports.views',
    url(r'^$', 'reports_app_view', (), name='reports_app_view'),
    url(r'^grammar/(?P<rep_type>\w+)$', 'reports_grammar_view', (), name='reports_grammar_view'),
    url(r'^parts/params-(?P<part_id>\w+).html$', 'reports_parts_params_view', (), name='reports_parts_params_view'),
    )

#eof
