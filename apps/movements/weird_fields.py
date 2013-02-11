# -*- encoding: utf-8 -*-
import logging
from django.utils.translation import ugettext_lazy as _

from django import forms
from django.template.loader import render_to_string
from django.utils.encoding import StrAndUnicode, force_unicode
from django.utils.safestring import mark_safe
from django.db.models import Count
from generic_views.forms import DetailForeignWidget
from django.forms.util import flatatt

from products.models import Manufacturer, ItemTemplate, ItemCategoryContain
from products.form_fields import CATItem

""" Fields used by the PO wizard
"""

class DummySupplierWidget(DetailForeignWidget):
    
    def value_from_datadict(self, data, files, name):
        """Instead of our widget (that is not rendered in the form), take either -vat or -name data
        """
        if data.get(name+'_name_or_vat') == 'vat':
            return data.get(name+'_vat', None)
        else:
            return data.get(name+'_name', None)

class ValidChoiceField(forms.ChoiceField):
    """ A ChoiceField that accepts any value in return data

        Used because choices are added in JavaScript, we don't know them here.
    """
    def valid_value(self, value):
        return True

class ItemsTreeWidget(forms.widgets.Widget):
    def render(self, name, value, attrs=None):
        if value is None:
            value = {}
        final_attrs = self.build_attrs(attrs)
        self.html_id = final_attrs.pop('id', name)
        context = {
            'name': name,
            'html_id': self.html_id,
            'items': value or [],
            'extra_attrs': mark_safe(flatatt(final_attrs)),
            'func_slug': self.html_id.replace("-","")
        }

        return mark_safe(render_to_string('po_wizard_treeitems.html', context))


class ItemsTreeField(forms.Field):
    widget = ItemsTreeWidget

    def to_python(self, value):
        print "value:", value
        return value

class _AttribsIter(object):
    def __init__(self, parent):
        self._parent = parent

    def __iter__(self):
        name = self._parent.did
        for cattr in self._parent._obj.category.attributes.all():
            yield CATItem(name, cattr, []) # value.get('all', []))

class IGW_Attribute(StrAndUnicode):
    def __init__(self, parent, obj, parts=None):
        self._parent = parent
        self._obj = obj
        self._parts = parts or []

    def __unicode__(self):
        return unicode(self._obj)

    @property
    def did(self):
        """div-id of this selection element
        """
        return mark_safe("%s-%d" %(self._parent.html_id, self._obj.id))

    @property
    def name(self):
        return self._obj.category.name

    @property
    def cat_id(self):
        return mark_safe(str(self._obj.category.id))

    @property
    def value(self):
        return self._obj.id

    @property
    def manufs(self):
        return Manufacturer.objects.filter(products__category=self._obj.category).\
                        annotate(num_products=Count('products')).order_by('-num_products')

    @property
    def parts(self):
        return self._parts

    @property
    def attribs(self):
        return _AttribsIter(self)

    @property
    def mandatory(self):
        return (self._obj.min_count > 0)

    @property
    def min_count(self):
        return self._obj.min_count

    @property
    def max_count(self):
        return self._obj.max_count

class ItemsGroupWidget(forms.widgets.Widget):
    """
        The value should be like::
        
            {   line_num: the line at step4 being edited
                item_template: the main product, in which we add parts
                parts: { may_contain.id: list[ tuple(object, quantity), ...] }
            }
    """

    def value_from_datadict(self, data, files, name):
        # TODO
        if name in data:
            # from step 3
            return data[name]
        elif ('id_%s_item_template' % name) in data:
            # it comes from form submission
            ret = {}
            # We have to decode the various fields:
            ret['item_template'] = ItemTemplate.objects.get(pk=data['id_%s_item_template' % name])
            ret['line_num'] = data.get('id_%s_line_num' % name, None)
            if ret['line_num']:
                ret['line_num'] = int(ret['line_num'])
            ret['parts'] = {}
            for mc in ret['item_template'].category.may_contain.all():
                pa = ret['parts'][mc.id] = []
                for dpart in data.getlist('id_%s-%d_parts' %(name, mc.id), []):
                    dpart_id = int(dpart) # TODO
                    pa.append((ItemTemplate.objects.get(pk=dpart_id, category=mc.category), 1))
            return ret
        else:
            return {}

    def bound_data(self, data, initial):
        if initial:
            ret = initial.copy()
        else:
            ret = {}
        if data:
            ret['all'] = data
        return ret

    def render(self, name, value, attrs=None):
        if value is None:
            value = {}
        final_attrs = self.build_attrs(attrs)
        self.html_id = final_attrs.pop('id', name)
        item_template = value.get('item_template', None)
        parts = value.get('parts', {})
        igroups = []
        if item_template is not None:
            for mc in item_template.category.may_contain.all():
                igroups.append(IGW_Attribute(self, mc, parts.get(mc.id, [])))
            # TODO fill previous data

        context = {
            'name': name,
            'html_id': self.html_id,
            'line_num': value.get('line_num', ''),
            'extra_attrs': mark_safe(flatatt(final_attrs)),
            'func_slug': self.html_id.replace("-",""),

            'item_template': item_template,
            'igroups': igroups,
        }

        return mark_safe(render_to_string('po_wizard_itemgroups.html', context))

class ItemsGroupField(forms.Field):
    widget = ItemsGroupWidget


# eof
