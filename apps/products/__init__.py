# -*- encoding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from common.api import register_links, register_menu, can_add, can_edit, can_delete, user_is_staff

from models import ItemTemplate, ItemCategory, Manufacturer, ProductAttribute

template_list = {'text':_('item templates'), 'view':'template_list', 'famfam':'page_go'}
template_pending_list = {'text':_('pending item templates'), 'view':'template_pending_list', 
        'famfam':'page_go', 'condition': user_is_staff }
template_create = {'text':_('create new template'), 'view':'template_create', 
        'famfam':'page_add', 'condition': can_add(ItemTemplate)}
template_orphan_list = {'text':_('orphans templates'), 'view':'template_orphans_list'}
template_update = {'text':_(u'edit'), 'view':'template_update', 'args':'object.id', 'famfam':'page_edit', 'condition': can_edit}
template_delete = {'text':_(u'delete'), 'view':'template_delete', 'args':'object.id', 'famfam':'page_delete', 'condition': can_delete}
template_photos = {'text':_(u'add / remove photos'), 'view':'template_photos', 'args':'object.id', 'famfam':'picture_go', 'condition': can_edit}
template_assets = {'text':_(u'related assets'), 'view':'template_items_list', 'args':'object.id', 'famfam':'computer_go'}
template_assign_supplies = {'text':_(u'assign supplies'), 'view':'template_assign_supply', 'args':'object.id', 'famfam':'monitor', 'condition': can_edit}
template_assign_suppliers = {'text':_(u'assign suppliers'), 'view':'template_assign_suppliers', 'args':'object.id', 'famfam':'lorry_go', 'condition': can_edit}

categories_list = {'text':_('categories'), 'view':'category_list', 'famfam':'page_go'}
categories_pending_list = {'text':_('pending categories'), 'view':'category_pending_list',
        'famfam':'page_go', 'condition': user_is_staff }
category_create = {'text':_('create new category'), 'view':'category_create', 
        'famfam':'page_add', 'condition': can_add(ItemCategory) }
category_update = {'text':_(u'edit category'), 'view':'category_update',
        'args':'object.id', 'famfam':'page_edit', 'condition': can_edit}
category_delete = {'text':_(u'delete category'), 'view':'category_delete',
        'args':'object.id', 'famfam':'page_delete', 'condition': can_delete }

attributes_list = {'text':_('attributes'), 'view':'attributes_list', 'famfam':'page_go',
        'condition': user_is_staff}
attributes_create = {'text':_('create new attribute'), 'view':'attributes_create', 
        'famfam':'page_add', 'condition': can_add(ProductAttribute) }
attributes_update = {'text':_(u'edit attribute'), 'view':'attributes_update',
        'args':'object.id', 'famfam':'page_edit', 'condition': can_edit}
attributes_delete = {'text':_(u'delete attribute'), 'view':'attributes_delete',
        'args':'object.id', 'famfam':'page_delete', 'condition': can_delete }

manufs_list = {'text':_('manufacturers'), 'view':'manufacturers_list', 'famfam':'page_go'}
manufacturer_create = {'text':_('create new manufacturer'), 'view':'manufacturer_create', 
        'famfam':'page_add', 'condition': can_add(Manufacturer) }
manufacturer_update = {'text':_(u'edit manufacturer'), 'view':'manufacturer_update', 
        'args':'object.id', 'famfam':'page_edit', 'condition': can_edit}
manufacturer_delete = {'text':_(u'delete manufacturer'), 'view':'manufacturer_delete', 
        'args':'object.id', 'famfam':'page_delete', 'condition': can_delete}

template_menu_links = [template_list, categories_list, manufs_list, attributes_list]

register_links(['template_list', 'template_create', 'template_view', 
                'template_orphans_list', 'template_update', 'template_delete', 
                'template_photos', 'template_assign_supply', 'template_assign_suppliers'],
            [template_create], menu_name='sidebar')

register_links(ItemTemplate, [dict(template_update, hide_text=True ), dict(template_assets, hide_text=True )])
register_links(ItemTemplate, [template_list, template_delete, template_photos, 
            template_assign_supplies], menu_name='sidebar')

register_links(['category_list'], [category_create], menu_name='sidebar')
register_links(ItemCategory, [categories_list, category_create,  category_delete], menu_name='sidebar')
register_links(ItemCategory, [category_update,])
register_links(Manufacturer, [manufs_list, manufacturer_create, manufacturer_update, manufacturer_delete], menu_name='sidebar')
register_links(['manufacturers_list'], [manufacturer_create], menu_name='sidebar')

register_links(['attributes_list'], [attributes_create], menu_name='sidebar')
register_links(ProductAttribute, [ attributes_update,] )
register_links(ProductAttribute, [ attributes_list, attributes_delete,], menu_name='sidebar')

register_menu([
    {'text':_('templates'), 'view':'template_list', 
            'links': template_menu_links, 'famfam':'page', 'position':3},
    ])

register_links(['home',], [template_pending_list, categories_pending_list ], menu_name='my_pending')

#eof