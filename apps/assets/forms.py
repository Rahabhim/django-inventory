# -*- encoding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.utils.html import conditional_escape

from generic_views.forms import DetailForm, ColumnsDetailWidget, \
        DetailForeignWidget, ReadOnlyInput, RModelForm

from models import Item, ItemGroup
from common.models import Location
from movements.models import Movement
from products.models import ItemTemplate
from ajax_select.fields import AutoCompleteSelectField

class ItemForm(RModelForm):
    class Meta:
        model = Item
        exclude = ('photos', 'active', 'is_bundled', 'qty')
        widgets = {'location': DetailForeignWidget(queryset=Location.objects.all()),
                    'item_template': DetailForeignWidget(queryset=ItemTemplate.objects.all()),
                    'property_number': ReadOnlyInput,
                    }

class ItemForm_view(DetailForm):
    class Meta:
        model = Item
        exclude = ('photos', 'active')

class ItemGroupForm(ItemForm):
    class Meta:
        model = ItemGroup
        exclude = ('items', 'active', 'is_bundled', 'qty')
        widgets = {'location': DetailForeignWidget(queryset=Location.objects.all()),
                    'item_template': DetailForeignWidget(queryset=ItemTemplate.objects.all()),
                    'property_number': ReadOnlyInput,
                    }

def _fmt_groupitem(item):
    href = False
    try:
        if item.item_template.category.is_bundle:
            href = item.itemgroup.get_absolute_url()
    except Exception, e:
        href = False
    if not href:
        href = item.get_absolute_url()
    return '<a href="%s">%s</a>' % (href, conditional_escape(unicode(item)))

class SubItemsDetailWidget(ColumnsDetailWidget):
    columns = [{'name': _(u'Contained Item'), 'format': _fmt_groupitem}, 
            {'name': _(u'Manufacturer'), 'attribute': 'item_template.manufacturer.name'},
            {'name': _(u'Category'), 'attribute': 'item_template.category.name'},
            ]
    order_by = 'item_template__category__name'

class ItemGroupForm_view(DetailForm):
    class Meta:
        model = ItemGroup
        widgets = {'items': SubItemsDetailWidget }

class ItemGroupForm_edit(ItemForm):
    class Meta:
        model = ItemGroup
        exclude = ('photos', 'active', 'is_bundled', 'qty')
        widgets = {'items': SubItemsDetailWidget,
                'location': DetailForeignWidget(queryset=Location.objects.all()),
                'item_template': DetailForeignWidget(queryset=ItemTemplate.objects.all()),
                    'property_number': ReadOnlyInput,
                }
                # read-only widget, edits must be done through special actions.

class ItemMovesWidget(ColumnsDetailWidget):
    columns = [ {'name': _('Date'), 'attribute': 'date_act'},
            {'name': _(u'Reference'), 'attribute': 'name' },
            {'name': _(u'From'), 'attribute':'location_src' },
            {'name': _(u'To'), 'attribute':'location_dest'},
            # {'name': _(u'State'), 'attribute':'get_state_display'},
            {'name': _(u'Type'), 'attribute':'get_stype_display'},]
    order_by = 'date_act'
    blind_mode = True # we trust the queryset from 'extra_fields' passed to us
    extra_filter = dict(state='done')

class ItemMovesForm_view(DetailForm):

    class Meta:
        model = Item
        exclude = ('photos', 'active', 'is_bundled', 'qty')
        widgets = {'movements': ItemMovesWidget }


#eof
