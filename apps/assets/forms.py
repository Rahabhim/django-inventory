# -*- encoding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext_lazy as _

from generic_views.forms import DetailForm, ColumnsDetailWidget, DetailForeignWidget, ReadOnlyInput

from models import Item, ItemGroup
from common.models import Location
from products.models import ItemTemplate
from ajax_select.fields import AutoCompleteSelectField

class ItemForm(forms.ModelForm):
    #item_template = AutoCompleteSelectField('product', label=_("product"), show_help_text=False)
    # location = AutoCompleteSelectField('location', label=_("current location"), required=False, show_help_text=False)
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

class SubItemsDetailWidget(ColumnsDetailWidget):
    columns = [{'name': _(u'Contained Item')}, 
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

#eof