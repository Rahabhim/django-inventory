# -*- encoding: utf-8 -*-
from django import forms
from generic_views.forms import DetailForm, InlineModelForm, ColumnsDetailWidget
from models import ItemTemplate, Manufacturer, ItemCategory, ItemCategoryContain, \
            ProductAttribute, ProductAttributeValue
from django.utils.translation import ugettext_lazy as _

class ItemTemplateForm(forms.ModelForm):
    class Meta:
        model = ItemTemplate
        exclude = ('photos', 'supplies', 'suppliers')

class ItemTemplateForm_view(DetailForm):
    class Meta:
        model = ItemTemplate
        exclude = ('photos',)

class ItemCategoryForm(forms.ModelForm):
    class Meta:
        model = ItemCategory

class ItemCategoryForm_view(DetailForm):
    class Meta:
        model = ItemCategory

class ItemCategoryContainForm(InlineModelForm):
    class Meta:
        model = ItemCategoryContain

class ItemCategoryContainForm_view(DetailForm):
    class Meta:
        model = ItemCategoryContain

class ProductAttributeForm(InlineModelForm):
    class Meta:
        model = ProductAttribute

class ProductAttributeForm_view(DetailForm):
    class Meta:
        model = ProductAttribute

class ProductAttributeValueForm(InlineModelForm):
    class Meta:
        model = ProductAttributeValue

class ProductAttributeValueForm_view(DetailForm):
    class Meta:
        model = ProductAttributeValue


class ManufacturerForm(forms.ModelForm):
    class Meta:
        model = Manufacturer

class ManufacturerForm_view(DetailForm):
    class Meta:
        model = Manufacturer



#eof