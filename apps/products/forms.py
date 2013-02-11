# -*- encoding: utf-8 -*-
from django import forms
from generic_views.forms import DetailForm, InlineModelForm, ColumnsDetailWidget
from models import ItemTemplate, Manufacturer, ItemCategory, ItemCategoryContain, \
            ProductAttribute, ProductAttributeValue, ItemTemplateAttributes
from django.utils.translation import ugettext_lazy as _
from form_fields import CategoriesAttributesField

class ItemTemplateForm(forms.ModelForm):
    attributes = CategoriesAttributesField(label=_("attributes"))

    def __init__(self, data=None, files=None, **kwargs):
        super(ItemTemplateForm, self).__init__(data, files, **kwargs)
        # Ugly hack: let our category be contained in initial data fed to
        # the field+widget
        if self.instance and self.instance.pk:
            self.initial['attributes'] = {'from_category': self.instance.category,
                'all': self.instance.attributes.values_list('value_id', flat=True) }
        else:
            self.initial['attributes'] = {}

    def save(self, commit=True):
        ret = super(ItemTemplateForm, self).save(commit=commit)
        # print "after s[h]ave:", self.cleaned_data
        if 'attributes' in self.cleaned_data:
            attrs = set(self.cleaned_data['attributes'])
            to_remove = []
            for aval in self.instance.attributes.all():
                if aval.value_id in attrs:
                    attrs.remove(aval.value_id)
                else:
                    aval.delete()
            if len(attrs):
                for attr in attrs:
                    self.instance.attributes.create(value_id=attr)
        return ret

    def _post_clean(self):
        """ Cleaning of `attributes` requires our instance, so call it again
        """
        super(ItemTemplateForm, self)._post_clean()
        name, field = 'attributes', self.base_fields['attributes']
        try:
            field.post_clean(self.instance, self.cleaned_data)
        except forms.ValidationError, e:
            self._errors[name] = self.error_class(e.messages)
            if name in self.cleaned_data:
                del self.cleaned_data[name]

    class Meta:
        model = ItemTemplate
        exclude = ('photos', 'supplies', 'suppliers')

class ItemTemplateForm_view(DetailForm):
    class Meta:
        model = ItemTemplate
        exclude = ('photos',)

class ItemTemplateAttributesForm(InlineModelForm):
    class Meta:
        model = ItemTemplateAttributes

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