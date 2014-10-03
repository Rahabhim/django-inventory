# -*- encoding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from django.utils.translation import ugettext_lazy as _
from generic_views.views import GenericBloatedListView
from models import SavedReport
from common.api import user_is_staff

title_filter = {'name': 'title', 'title': _('Title'), 'destination':'title__icontains'}

def _get_model_choices(**kwargs):
    from views import get_allowed_rtypes, get_rtype_name
    choices = [('', '*')]
    if 'parent' in kwargs:
        context = {'request': kwargs['parent'].request, 'user': kwargs['parent'].request.user}
        for rt in get_allowed_rtypes(context):
            choices.append((rt, get_rtype_name(rt).title()))
    return choices

model_filter = {'name': 'rmodel', 'title': _('Model'), 'destination':'rmodel',
                'condition': user_is_staff,
                'choices': _get_model_choices }

urlpatterns = patterns('reports.views',
    url(r'^$', 'reports_app_view', (), name='reports_app_view'),
    url(r'^list$', GenericBloatedListView.as_view(
                queryset=SavedReport.objects.by_request,
                list_filters=[title_filter, model_filter],
                extra_columns=[ {'name':_(u'Report Model'), 'attribute': 'fmt_model', 'order_attribute': 'rmodel'},
                            ],
                title=_(u'list of saved reports')),
            name='reports_list_view'),
    url(r'^details/(?P<pk>\d+)/$', 'report_details_view', name='report_details_view'),
    url(r'^grammar/(?P<rep_type>\w+)$', 'reports_grammar_view', (), name='reports_grammar_view'),
    url(r'^cat-grammar/(?P<cat_id>\d+)$', 'reports_cat_grammar_view', (), name='reports_cat_grammar_view'),
    url(r'^parts/params-(?P<part_id>\w+).html$', 'reports_parts_params_view', (), name='reports_parts_params_view'),
    url(r'^results-preview/(?P<rep_type>\w+)$', 'reports_get_preview', (), name='reports_get_preview'),

    # Results, in static POST responses
    url(r'^results.html$', 'reports_results_html', (), name='reports_results_html'),
    url(r'^results.pdf', 'reports_results_pdf', (), name='reports_results_pdf'),
    url(r'^results.csv', 'reports_results_csv', (), name='reports_results_csv'),

    # Public results, bypassing Django authentication
    url(r'^pub/results.html$', 'reports_results_html', (), name='reports_pub_results_html'),
    url(r'^pub/results.json$', 'reports_results_json', (), name='reports_pub_results_json'),
    url(r'^pub/results.csv$', 'reports_results_csv', (), name='reports_pub_results_csv'),

    # back API
    url(r'^back/list', 'reports_back_list_view', (), name='reports_back_list_view'),
    url(r'^back/load', 'reports_back_load_view', (), name='reports_back_load_view'),
    url(r'^back/save', 'reports_back_save_view', (), name='reports_back_save_view'),
    url(r'^back/delete', 'reports_back_del_view', (), name='reports_back_del_view'),
    )

#eof
