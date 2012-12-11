# -*- encoding: utf-8 -*-
from django.conf.urls.defaults import patterns, url

from django.utils.translation import ugettext_lazy as _
from django.views.generic.create_update import create_object, update_object

from generic_views.views import generic_delete, \
                                generic_detail, generic_list, GenericBloatedListView


from models import Delegate, Project, Contract
from forms import DelegateForm, DelegateForm_view, \
        ProjectForm, ProjectForm_view, ContractForm, ContractForm_view

urlpatterns = patterns('procurements.views',
    url(r'^delegate/list/$', GenericBloatedListView.as_view(queryset=Delegate.objects.all(),
            extra_columns=[{'name': _("Active"), 'attribute': 'active'},],
            title=_(u'delegates list')), name='delegate_list'),
    url(r'^delegate/create/$', create_object, {'form_class': DelegateForm,
                    'template_name':'generic_form.html',
                    'extra_context':{'object_name':_(u'delegate')}},
            'delegate_create'),
    url(r'^delegate/(?P<object_id>\d+)/update/$', update_object,
            {'form_class': DelegateForm, 'template_name':'generic_form.html',
                    'extra_context':{'object_name':_(u'delegate')}},
            'delegate_update' ),
    url(r'^delegate/(?P<object_id>\d+)/delete/$', generic_delete,
            dict(model=Delegate, post_delete_redirect="delegate_list",
                    extra_context=dict(object_name=_(u'delegate'),
                    _message=_(u"Will delete delegate and all references in contracts"))),
            'delegate_delete' ),
    url(r'^delegate/(?P<object_id>\d+)/$', generic_detail, dict(form_class=DelegateForm_view,
                    queryset=Delegate.objects.all(),
                    extra_context={'object_name':_(u'delegate'),}),
            'delegate_view'),

    url(r'^contracts/list/$', GenericBloatedListView.as_view(queryset=Contract.objects.all(),
            extra_columns=[{'name': _("Department"), 'attribute': 'department'},
                        {'name': _("Date"), 'attribute': 'date_start'},
                        {'name': _("Delegate"), 'attribute': 'delegate'},
                            ],
            prefetch_fields=('department', 'delegate'),
            title=_(u'list of contracts')), name='contract_list'),
    url(r'^contracts/create/$', create_object, {'form_class': ContractForm,
                    'template_name':'generic_form.html',
                    'extra_context':{'object_name':_(u'contract')}},
            'contract_create'), # TODO: permissions?
    url(r'^contracts/(?P<object_id>\d+)/update/$', update_object,
            {'form_class':ContractForm, 'template_name':'generic_form.html',
                    'extra_context':{'object_name':_(u'contract')}},
            'contract_update' ),
    url(r'^contracts/(?P<object_id>\d+)/delete/$', generic_delete,
            dict(model=Contract, post_delete_redirect="contract_list",
                    extra_context=dict(object_name=_(u'contract'),
                    # FIXME _message=_(u"Will be deleted from any user that may have it assigned and from any item group.")
                    )),
            'contract_delete' ),
    url(r'^contracts/(?P<object_id>\d+)/$', generic_detail, dict(form_class=ContractForm_view,
                    queryset=Contract.objects.all(),
                    extra_context={'object_name':_(u'contract'),}),
            'contract_view'),

    url(r'^projects/list/$', GenericBloatedListView.as_view(queryset=Project.objects.all(),
            title=_(u'list of projects')), name='projects_list'),
    url(r'^projects/create/$', create_object, {'form_class':ProjectForm,
                    'template_name':'generic_form.html',
                    'extra_context':{'object_name':_(u'project')}},
            'project_create'),
    url(r'^projects/(?P<object_id>\d+)/update/$', update_object,
            {'form_class': ProjectForm, 'template_name':'generic_form.html',
                    'extra_context':{'object_name':_(u'project')}},
            'project_update' ),
    url(r'^projects/(?P<object_id>\d+)/delete/$', generic_delete,
            dict(model=Project, post_delete_redirect="projects_list",
                    extra_context=dict(object_name=_(u'project'),
                    # FIXME _message=_(u"Will be deleted from any user that may have it assigned and from any item group.")
                    )),
            'project_delete' ),
    url(r'^projects/(?P<object_id>\d+)/$', generic_detail, dict(form_class=ProjectForm_view,
                    queryset=Project.objects.all(),
                    extra_context={'object_name':_(u'project'),}),
            'project_view'),

    )

#eof
