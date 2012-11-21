# -*- encoding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from django.utils.translation import ugettext_lazy as _
from django.views.generic.create_update import create_object, update_object

from generic_views.views import generic_delete, \
                                generic_detail, generic_list, \
                                GenericUpdateView

from photos.views import generic_photos

from models import Item, ItemGroup, State
from forms import ItemForm, ItemForm_view, ItemGroupForm, ItemGroupForm_view, ItemGroupForm_edit
from conf import settings as asset_settings
from views import AssetListView, LocationAssetsView, DepartmentAssetsView

urlpatterns = patterns('assets.views',

    url(r'^asset/create/$', create_object, {'form_class':ItemForm, 'template_name':'generic_form.html'}, 'item_create'),
    url(r'^asset/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(form_class=ItemForm, 
                template_name='item_group_form.html', 
                extra_context={'object_name':_(u'asset')}), name='item_update'),
    url(r'^asset/(?P<object_id>\d+)/delete/$', generic_delete, dict({'model':Item}, post_delete_redirect="item_list", extra_context=dict(object_name=_(u'asset'))), 'item_delete'),
    url(r'^asset/list/$', AssetListView.as_view(title=_(u'list of assets')), name='item_list'),
    url(r'^asset/(?P<object_id>\d+)/$', generic_detail, dict(form_class=ItemForm_view, 
                template_name="asset_detail.html",
                queryset=Item.objects.all(), 
                extra_context={'object_name':_(u'asset'), 
                        'sidebar_subtemplates':['generic_photos_subtemplate.html', 
                                                'state_subtemplate.html']}, 
                extra_fields=[{'field':'get_owners', 'label':_(u'Assigned to:')}]),
            'item_view'),
    url(r'^asset/(?P<object_id>\d+)/photos/$', generic_photos, {'model':Item, 'max_photos':asset_settings.MAX_ASSET_PHOTOS, 'extra_context':{'object_name':_(u'asset')}}, 'item_photos'),
    url(r'^asset/(?P<object_id>\d+)/state/(?P<state_id>\d+)/set/$', 'item_setstate', (), 'item_setstate'),
    url(r'^asset/(?P<object_id>\d+)/state/(?P<state_id>\d+)/unset$', 'item_remove_state', (), 'item_remove_state'),

    url(r'^group/list/$', generic_list, dict(queryset=ItemGroup.objects.by_request,
                extra_context=dict(title=_(u'item groups'),
                        extra_columns=[{'name': _('Location'), 'attribute': 'current_location'},
                                    {'name': _(u'Manufacturer'), 'attribute': 'get_manufacturer'},
                                    {'name': _(u'Category'), 'attribute': 'get_category'},]),), 'group_list'),
    # my items?
    url(r'^group/create/$', create_object, {'form_class':ItemGroupForm, 'template_name':'generic_form.html'}, 'group_create'),
    url(r'^group/(?P<object_id>\d+)/$', generic_detail, dict(form_class=ItemGroupForm_view, 
                            template_name="asset_detail.html",
                            queryset=ItemGroup.objects.all()), name='group_view'),
    url(r'^group/(?P<pk>\d+)/update/$', GenericUpdateView.as_view(form_class=ItemGroupForm_edit,
            template_name='item_group_form.html',
            extra_context={'title':_(u'Edit item group')}), name='group_update'),
    url(r'^group/(?P<object_id>\d+)/delete/$', generic_delete, dict({'model':ItemGroup}, post_delete_redirect="group_list", extra_context=dict(object_name=_(u'item group'))), 'group_delete'),

    url(r'^state/list/$', generic_list, dict({'queryset':State.objects.all()}, extra_context=dict(title =_(u'states'))), 'state_list'),
    url(r'^state/create/$', create_object, {'model':State, 'template_name':'generic_form.html', 'extra_context':{'title':'create asset state'}}, 'state_create'),
    url(r'^state/(?P<object_id>\d+)/update/$', update_object, {'model':State, 'template_name':'generic_form.html'}, 'state_update'),
    url(r'^state/(?P<object_id>\d+)/delete/$', generic_delete, dict({'model':State}, post_delete_redirect="state_list", extra_context=dict(object_name=_(u'states'))), 'state_delete'),
    
    url(r'^location/(?P<loc_id>\d+)/assets/$', LocationAssetsView.as_view(), name='location_assets'),
    url(r'^department/(?P<dept_id>\d+)/assets/$', DepartmentAssetsView.as_view(), name='department_assets'),
)


