# -*- encoding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from django.utils.translation import ugettext_lazy as _

from generic_views.views import GenericDeleteView, GenericBloatedListView, \
                GenericCreateView, GenericUpdateView #, GenericDetailView

from models import HelpTopic
from forms import HelpTopicForm

title_filter = {'name': 'title', 'title': _('Title'), 'destination':'title__icontains'}

tkey_filter = {'name': 'tkey', 'title': _('key'), 'destination':'tkey__startswith'}

mode_filter = {'name':'mode', 'title':_(u'mode'), 
            'choices':'dhelp.HelpTopic.mode' , 'destination':'mode'}

active_filter = {'name': 'active', 'title': _('active'), 'destination': 'active'}

urlpatterns = patterns('dhelp.views',
    url(r'^topic/list/$', GenericBloatedListView.as_view(
                queryset=HelpTopic.objects.by_request,
                list_filters=[title_filter, mode_filter, tkey_filter, active_filter],
                extra_columns=[ {'name':_(u'Mode'), 'attribute': 'mode'},
                            {'name':_(u'Key'), 'attribute': 'tkey'},
                            {'name':_(u'Active'), 'attribute': 'active'},
                            {'name': _("Sequence"), 'attribute': 'sequence'},
                            ],
                title=_(u'list of help topics')),
            name='help_topic_list'),
    url(r'^topic/(?P<object_id>\d+)$', 'help_display_view', (), name='help_topic_view'),
    url(r'^topic/create/$', GenericCreateView.as_view(
                form_class=HelpTopicForm, extra_context={'title':_(u'create new help topic'),
                                                         'novalidate': True}),
            name='help_topic_create'),
    url(r'^topic/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(
                form_class=HelpTopicForm, extra_context={'novalidate': True}),
            name='help_topic_update'),
    url(r'^topic/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(model=HelpTopic,
                success_url="help_topic_list",
                extra_context=dict(object_name=_(u'help topic'))),
            name='help_topic_delete'),

    url(r'^t/(?P<object_id>\d+)$', 'help_display_view', (), name='help_display_view'),

    url(r'^i/(?P<mode>.+)/(?P<tkey>.+)$', 'help_index_view', name='help_topic2_view'),
    url(r'^$', 'help_index_view', (), name='help_index_view'),
    )

#eof
