# -*- encoding: utf-8 -*-
from django.conf.urls.defaults import patterns, url

from django.utils.translation import ugettext_lazy as _

from generic_views.views import GenericBloatedListView, GenericDeleteView, \
                GenericDetailView, GenericCreateView, GenericUpdateView


from models import Delegate, Project, Contract
from forms import DelegateForm, DelegateForm_view, \
        ProjectForm, ProjectForm_view, ContractForm, ContractForm_view

urlpatterns = patterns('procurements.views',
    url(r'^delegate/list/$', GenericBloatedListView.as_view(queryset=Delegate.objects.all(),
            extra_columns=[{'name': _("Active"), 'attribute': 'active'},],
            title=_(u'delegates list')), name='delegate_list'),
    url(r'^delegate/create/$', GenericCreateView.as_view(form_class=DelegateForm,
                    extra_context={'object_name':_(u'delegate')}),
            name='delegate_create'),
    url(r'^delegate/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(form_class=DelegateForm,
                    extra_context={'object_name':_(u'delegate')}),
            name='delegate_update' ),
    url(r'^delegate/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(
                model=Delegate, success_url="delegate_list",
                    extra_context=dict(object_name=_(u'delegate'),)),
            name='delegate_delete' ),
    url(r'^delegate/(?P<pk>\d+)/$', GenericDetailView.as_view(form_class=DelegateForm_view,
                    queryset=Delegate.objects.all(),
                    extra_context={'object_name':_(u'delegate'),}),
            name='delegate_view'),

    url(r'^contracts/list/$', GenericBloatedListView.as_view(queryset=Contract.objects.all(),
            extra_columns=[{'name': _("Department"), 'attribute': 'department'},
                        {'name': _("Date"), 'attribute': 'date_start'},
                        {'name': _("Delegate"), 'attribute': 'delegate'},
                            ],
            prefetch_fields=('department', 'delegate'),
            title=_(u'list of contracts')), name='contract_list'),
    url(r'^contracts/create/$', GenericCreateView.as_view(form_class= ContractForm,
                    extra_context={'object_name':_(u'contract')}),
            name='contract_create'),
    url(r'^contracts/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(form_class=ContractForm,
                    extra_context={'object_name':_(u'contract')}),
            name='contract_update' ),
    url(r'^contracts/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(
                model=Contract, success_url="contract_list",
                    extra_context=dict(object_name=_(u'contract'), )),
            name='contract_delete' ),
    url(r'^contracts/(?P<pk>\d+)/$', GenericDetailView.as_view(form_class=ContractForm_view,
                    queryset=Contract.objects.all(),
                    extra_context={'title':_(u'Contract details'),}),
            name='contract_view'),
    url(r'^contracts/(?P<pk>\d+)/get_description/$','contract_get_description', (), 
            name="contract_get_description"),
    url(r'^projects/list/$', GenericBloatedListView.as_view(queryset=Project.objects.all(),
            title=_(u'list of projects')), name='projects_list'),
    url(r'^projects/create/$', GenericCreateView.as_view(form_class=ProjectForm,
                    extra_context={'object_name':_(u'project')}),
            name='project_create'),
    url(r'^projects/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(form_class= ProjectForm,
                    extra_context={'object_name':_(u'project')}),
            name='project_update' ),
    url(r'^projects/(?P<pk>\d+)/delete/$', GenericDeleteView.as_view(
                model=Project, success_url="projects_list",
                    extra_context=dict(object_name=_(u'project'), )),
            name='project_delete' ),
    url(r'^projects/(?P<pk>\d+)/$', GenericDetailView.as_view(form_class=ProjectForm_view,
                    queryset=Project.objects.all(),
                    extra_context={'object_name':_(u'project'),}),
            name='project_view'),

    )

#eof
