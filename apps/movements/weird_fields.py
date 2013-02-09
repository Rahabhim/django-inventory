# -*- encoding: utf-8 -*-
import logging
from django.utils.translation import ugettext_lazy as _

from django import forms
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from generic_views.forms import DetailForeignWidget
from django.forms.util import flatatt

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

