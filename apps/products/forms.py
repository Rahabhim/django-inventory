# -*- encoding: utf-8 -*-
from django import forms
from generic_views.forms import DetailForm, InlineModelForm, \
            ROModelChoiceField, DetailPlainForeignWidget #, ColumnsDetailWidget
from models import ItemTemplate, Manufacturer, ItemCategory, ItemCategoryContain, \
            ProductAttribute, ProductAttributeValue, ItemTemplateAttributes, \
            ItemTemplatePart, ItemTemplateNumAlias
from django.utils.translation import ugettext_lazy as _
from form_fields import CategoriesAttributesField
from ajax_select.fields import AutoCompleteSelectField
from django.contrib import messages

from movements.weird_fields import ItemsGroupWidget
from collections import defaultdict
import logging

logger = logging.getLogger('apps.products.forms')


class ItemsPartsGroupWidget(ItemsGroupWidget):
    _template_name = 'product_itemparts.html'

class ItemsPartsGroupField(forms.Field):
    """ value = {
                item_template: the main product, in which we add parts
                parts: { may_contain.id: list[ tuple(object, quantity), ...] }
            }
    """
    widget = ItemsPartsGroupWidget

class ItemTemplateForm(forms.ModelForm):
    attributes = CategoriesAttributesField(label=_("attributes"))
    parts = ItemsPartsGroupField(label=_("standard parts"), required=False)

    def __init__(self, data=None, files=None, **kwargs):
        super(ItemTemplateForm, self).__init__(data, files, **kwargs)
        # Ugly hack: let our category be contained in initial data fed to
        # the field+widget
        if self.instance and self.instance.pk:
            self.initial['attributes'] = {'from_category': self.instance.category,
                'all': self.instance.attributes.values_list('value_id', flat=True) }

            if self.instance.category.is_group or self.instance.category.is_bundle:
                std_parts = defaultdict(list)
                for sp in self.instance.parts.all():
                    std_parts[sp.item_template.category_id].\
                                append((sp.item_template, sp.qty))

                parts_parts = {}
                for mc in self.instance.category.may_contain.all():
                    parts_parts[mc.id] = std_parts.pop(mc.category_id, [])

                if std_parts:
                    logger.warning("Stray standard parts found for template %s: %r",
                                self.instance, std_parts)
                self.initial['parts'] = { 'item_template': self.instance,
                            'parts': parts_parts }
        else:
            self.initial['attributes'] = {}
            self.initial['parts'] = None

    def save(self, commit=True):
        ret = super(ItemTemplateForm, self).save(commit=commit)
        # print "after s[h]ave:", self.cleaned_data
        if 'attributes' in self.cleaned_data:
            attrs = set(self.cleaned_data['attributes'])
            for aval in self.instance.attributes.all():
                if aval.value_id in attrs:
                    attrs.remove(aval.value_id)
                else:
                    aval.delete()
            if len(attrs):
                for attr in attrs:
                    self.instance.attributes.create(value_id=attr)
        if 'parts' in self.cleaned_data:
            bits = {} # arrange all bundled parts in dict
                          # by part.item_template.id
            item = self.cleaned_data['parts']
            for pcats in item.get('parts',{}).values():
                for p, q in pcats:
                    n = bits.get(p.id, (p, 0))[1]
                    bits[p.id] = (p, n + q)
            for bitem in self.instance.parts.all():
                if bitem.item_template_id not in bits:
                    bitem.delete()
                else:
                    p, q = bits.pop(bitem.item_template_id)
                    if bitem.qty != q:
                        bitem.qty = q
                        bitem.save()
            for p, q in bits.values():
                self.instance.parts.create(item_template=p, qty=q)
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

class ItemTemplateRequestForm_base(forms.ModelForm):
    """Request a new Product, from non-admin users

        This is taken from PO_Wizard step 3a
    """
    description = forms.fields.CharField(label=_(u"product name"))
    url = forms.fields.CharField(max_length=256, required=False, label=_(u'Product URL'),
            help_text=_("Please enter the URL of the manufacturer for this product"))

    class Meta:
        model = ItemTemplate
        fields = ('description', 'category', 'manufacturer', 'part_number', 'url', 'notes')

    def _send_request(self):
        """Sends notification about the pending ItemTemplate
        """
        # Hint: use self.instance
        pass

class ItemTemplateRequestForm(ItemTemplateRequestForm_base):

    def _set_request(self, request):
        self._request = request

    def save(self, commit=True):
        ret = super(ItemTemplateRequestForm, self).save(commit=commit)
        try:
            self._send_request()
            messages.info(self._request, _("Your request for %s has been stored. An administrator of the Helpdesk will review it and come back to you.") % \
                    self.instance.description)
        except Exception:
            logger.exception("Helpdesk request fail:")
            messages.error(self._request, _("The data you have entered has been saved, but the Helpdesk has NOT been notified, due to an internal error."))
        return ret

class ItemPNAliasForm_inline(InlineModelForm):
    class Meta:
        model = ItemTemplateNumAlias

class ItemPNAliasFormD_inline(DetailForm):
    class Meta:
        model = ItemTemplateNumAlias

class ItemPartsForm_inline(InlineModelForm):
    item_template = AutoCompleteSelectField('product', show_help_text=False, required=False,
            label=_("Template"))

    class Meta:
        model = ItemTemplatePart
        verbose_name=_("Standard Parts")

class ItemPartsFormD_inline(InlineModelForm):
    item_template = ROModelChoiceField(ItemTemplate.objects.all(),
                widget=DetailPlainForeignWidget, label=_('Template'))
    class Meta:
        model = ItemTemplatePart
        verbose_name=_("Standard Parts")

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