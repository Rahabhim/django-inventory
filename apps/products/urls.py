from django.conf.urls.defaults import patterns, url

from django.utils.translation import ugettext_lazy as _
from django.views.generic.create_update import create_object, update_object

from conf import settings as inventory_settings

from photos.views import generic_photos

from generic_views.views import generic_delete, \
                                generic_detail, generic_list

from models import ItemTemplate
from forms import ItemTemplateForm, ItemTemplateForm_view

urlpatterns = patterns('products.views',
    url(r'^template/list/$', generic_list, dict({'queryset':ItemTemplate.objects.all()},
            extra_context=dict(title=_(u'item template'))), 'template_list'),
    url(r'^template/create/$', create_object, {'form_class':ItemTemplateForm,
                    'template_name':'generic_form.html',
                    'extra_context':{'object_name':_(u'item template')}},
            'template_create'),
    url(r'^template/(?P<object_id>\d+)/update/$', update_object,
            {'form_class':ItemTemplateForm, 'template_name':'generic_form.html',
                    'extra_context':{'object_name':_(u'item template')}},
            'template_update' ),
    url(r'^template/(?P<object_id>\d+)/delete/$', generic_delete,
            dict(model=ItemTemplate, post_delete_redirect="template_list",
                    extra_context=dict(object_name=_(u'item template'),
                    _message=_(u"Will be deleted from any user that may have it assigned and from any item group."))),
            'template_delete' ),
    url(r'^template/orphans/$', generic_list, dict(queryset=ItemTemplate.objects.filter(item=None),
                    extra_context=dict(title=_('orphan templates'))),
            'template_orphans_list'),
    url(r'^template/(?P<object_id>\d+)/photos/$', generic_photos, {'model':ItemTemplate, 'max_photos':inventory_settings.MAX_TEMPLATE_PHOTOS, 'extra_context':{'object_name':_(u'item template')}}, 'template_photos'),
    url(r'^template/(?P<object_id>\d+)/$', generic_detail, dict(form_class=ItemTemplateForm_view,
                    queryset=ItemTemplate.objects.all(),
                    extra_context={'object_name':_(u'item template'), \
                        'sidebar_subtemplates':['generic_photos_subtemplate.html']}),
            'template_view'),
    url(r'^template/(?P<object_id>\d+)/items/$', 'template_items', (), 'template_items_list'),
    url(r'^template/(?P<object_id>\d+)/assign/supplies$', 'template_assign_remove_supply', (), name='template_assign_supply'),
    url(r'^template/(?P<object_id>\d+)/assign/suppliers/$', 'template_assign_remove_suppliers', (), name='template_assign_suppliers'),

    url(r'^supplier/(?P<object_id>\d+)/assign/itemtemplates/$',
            'supplier_assign_remove_itemtemplates', (), 'supplier_assign_itemtemplates'),
    )

#TODO: categories, attributes, manufacturers

#eof
