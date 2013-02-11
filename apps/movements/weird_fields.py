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

from products.models import Manufacturer
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
    def __init__(self, parent, obj):
        self._parent = parent
        self._obj = obj

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
    def attribs(self):
        return _AttribsIter(self)

class ItemsGroupWidget(forms.widgets.Widget):

    def value_from_datadict(self, data, files, name):
        # TODO
        #if isinstance(data, QueryDict):
            ## it comes from form submission
            #pass
        #elif isinstance(data, MultiValueDict):
            ## from step 3
            #pass
        return data.get(name, {})

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
        optional_groups = []
        mandatory_groups = []
        if item_template is not None:
            for mc in item_template.category.may_contain.all():
                if mc.min_count > 0:
                    mandatory_groups.append(IGW_Attribute(self, mc))
                else:
                    optional_groups.append(IGW_Attribute(self, mc))
            # TODO fill previous data

        context = {
            'name': name,
            'html_id': self.html_id,
            'extra_attrs': mark_safe(flatatt(final_attrs)),
            'func_slug': self.html_id.replace("-",""),

            'item_template': item_template,
            'optional_groups': optional_groups,
            'mandatory_groups': mandatory_groups,
        }

        return mark_safe(render_to_string('po_wizard_itemgroups.html', context))

class ItemsGroupField(forms.Field):
    widget = ItemsGroupWidget


# eof
