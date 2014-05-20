# -*- encoding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from django.utils.translation import ugettext_lazy as _
from generic_views.views import GenericBloatedListView
from models import SavedReport
from common.api import user_is_staff

title_filter = {'name': 'title', 'title': _('Title'), 'destination':'title__icontains'}

model_filter = {'name': 'model', 'title': _('Model'), 'destination':'model',
                'condition': user_is_staff }

urlpatterns = patterns('reports.views',
    url(r'^$', 'reports_app_view', (), name='reports_app_view'),
    url(r'^list$', GenericBloatedListView.as_view(
                queryset=SavedReport.objects.by_request,
                list_filters=[title_filter, model_filter],
                extra_columns=[ {'name':_(u'Model'), 'attribute': 'model'},
                            ],
                title=_(u'list of saved reports')),
            name='reports_list_view'),
    url(r'^grammar/(?P<rep_type>\w+)$', 'reports_grammar_view', (), name='reports_grammar_view'),
    url(r'^cat-grammar/(?P<cat_id>\d+)$', 'reports_cat_grammar_view', (), name='reports_cat_grammar_view'),
    url(r'^parts/params-(?P<part_id>\w+).html$', 'reports_parts_params_view', (), name='reports_parts_params_view'),
    url(r'^results-preview/(?P<rep_type>\w+)$', 'reports_get_preview', (), name='reports_get_preview'),
    
    # back API
    url(r'^back/list', 'reports_back_list_view', (), name='reports_back_list_view'),
    url(r'^back/load', 'reports_back_load_view', (), name='reports_back_load_view'),
    url(r'^back/save', 'reports_back_save_view', (), name='reports_back_save_view'),
    url(r'^back/delete', 'reports_back_del_view', (), name='reports_back_del_view'),
    )

#eof
