from django.utils.translation import ugettext_lazy as _

from common.api import register_links, register_menu

from models import ItemTemplate
import models


template_list = {'text':_('view all'), 'view':'template_list', 'famfam':'page_go'}
template_create = {'text':_('create new template'), 'view':'template_create', 'famfam':'page_add'}
template_orphan_list = {'text':_('orphans templates'), 'view':'template_orphans_list'}
template_update = {'text':_(u'edit'), 'view':'template_update', 'args':'object.id', 'famfam':'page_edit'}
template_delete = {'text':_(u'delete'), 'view':'template_delete', 'args':'object.id', 'famfam':'page_delete'}
template_photos = {'text':_(u'add / remove photos'), 'view':'template_photos', 'args':'object.id', 'famfam':'picture_go'}
template_assets = {'text':_(u'related assets'), 'view':'template_items_list', 'args':'object.id', 'famfam':'computer_go'}
template_assign_supplies = {'text':_(u'assign supplies'), 'view':'template_assign_supply', 'args':'object.id', 'famfam':'monitor'}
template_assign_suppliers = {'text':_(u'assign suppliers'), 'view':'template_assign_suppliers', 'args':'object.id', 'famfam':'lorry_go'}

categories_list = {'text':_('categories'), 'view':'category_list', 'famfam':'page_go'}
manufs_list = {'text':_('manufacturers'), 'view':'manufacturers_list', 'famfam':'page_go'}

template_menu_links = [template_list, template_orphan_list, categories_list, manufs_list]

register_links(['template_list', 'template_create', 'template_view', 
                'template_orphans_list', 'template_update', 'template_delete', 
                'template_photos', 'template_assign_supply', 'template_assign_suppliers'],
            [template_create], menu_name='sidebar')
register_links(ItemTemplate, [template_update, template_delete, template_photos, 
            template_assets, template_assign_supplies, template_assign_suppliers])

register_menu([
    {'text':_('templates'), 'view':'template_list', 
            'links': template_menu_links, 'famfam':'page', 'position':4},
    ])
