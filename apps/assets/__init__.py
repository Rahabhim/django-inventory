from django.utils.translation import ugettext_lazy as _

from common.api import register_links, register_menu, role_from_request

from models import State, Item, ItemGroup
import models


def asset_is_ours(obj, context):
    return Item.objects.by_request(context['request']).filter(id=obj.id).exists()

state_list = {'text':_('assets states'), 'view':'state_list', 'famfam':'error_go'}
state_create = {'text':_('create new asset state'), 'view':'state_create', 'famfam':'error_add'}
state_edit = {'text':_(u'edit asset state'), 'view':'state_update', 'args':'object.id', 'famfam':'error'}
state_delete = {'text':_(u'delete asset state'), 'view':'state_delete', 'args':'object.id', 'famfam':'error_delete'}


asset_list = {'text':_('list all assets'), 'view':'item_list', 'famfam':'computer'}
# asset_create = {'text':_('create new asset'), 'view':'item_create', 'famfam':'computer_add'}
asset_edit = {'text':_(u'edit serials'), 'view':'item_update', 'args':'object.id', 'famfam':'computer_edit', 'condition':  asset_is_ours}
# asset_delete = {'text':_(u'delete'), 'view':'item_delete', 'args':'object.id', 'famfam':'computer_delete'}
asset_photos = {'text':_(u'add / remove photos'), 'view':'item_photos', 'args':'object.id', 'famfam':'picture_edit', 'condition':  asset_is_ours}
asset_template = {'text':_(u'template'), 'view':'template_view', 'args':'object.item_template.id', 'famfam':'page_go'}
asset_history = {'text':_(u'trace'), 'view':'item_history_view', 'args':'object.id', 'famfam':'book_open', 'condition':  asset_is_ours}
asset_printout = {'text':_(u'printout'), 'view':'asset_printout', 'args':'object.id', 'famfam':'print', 'condition':  asset_is_ours}


group_list = {'text':_(u'list all groups'), 'view':'group_list', 'famfam':'chart_pie'}
group_edit = {'text':_(u'edit serials'), 'view':'group_update', 'args':'object.item_ptr.id', 'famfam':'computer_edit'}

#group_create = {'text':_(u'create group'), 'view':'group_create', 'famfam':'chart_pie_add'}
#group_update = {'text':_(u'edit'), 'view':'group_update', 'args':'object.id', 'famfam':'chart_pie_edit'}
#group_delete = {'text' : _(u'delete'), 'view':'group_delete', 'args':'object.id', 'famfam':'chart_pie_delete'}

state_filter = {'name':'state', 'title':_(u'state'), 'queryset':State.objects.all(), 'destination':'itemstate'}


#register_links(['item_list', 'item_view',
        #'item_update_serials', 'item_delete', 'item_photos',
        #'template_items_list'], [asset_create], menu_name='sidebar')

register_links(Item, [asset_edit, asset_history, asset_printout], menu_name='sidebar')

register_links(ItemGroup, [group_edit, asset_template, asset_history, asset_printout])

register_links(['state_list', 'state_create', 'state_update', 'state_delete'], [state_create], menu_name='sidebar')
register_links(State, [state_edit, state_delete])

register_links(['home'], [asset_list,], menu_name='start_actions')

register_menu([
    {'text':_('assets'), 'view':'item_list', 'id': 'menu_assets',
        'links':[ asset_list,
                ],
        'famfam':'computer', 'position':2},
    ])

def _has_active_role(obj, context):
    return bool(role_from_request(context['request']))

asset_list_printout = {'text':_('print assets list'), 'view':'asset_list_printout2',
            'famfam':'printer', 'condition': _has_active_role }
register_links(['item_list',], [asset_list_printout,], menu_name='sidebar')


register_links(['department_assets',], [ {'text':_('print assets list'), \
            'view':'asset_list_printout','args':'department.id', 'famfam':'printer'} ], \
        menu_name='sidebar')
#eof
