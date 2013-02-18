# -*- encoding: utf-8 -*-
import logging
from collections import defaultdict
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

    The wizard is mainly built using custom widgets, with a mixture of http and
    JS logic.
"""

logger = logging.getLogger('apps.movements.po_wizard')

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

class ItemsTreePart(object):
    """ A leaf part contained in some TreeItem
    """
    def __init__(self, item, quantity):
        self.item = item
        self.quantity = quantity

class ItemsTreeCat(object):
    """ A category node contained in TreeItem, having TreeParts
    """
    def __init__(self, may_contain_id, pqs):
        self._mc = ItemCategoryContain.objects.get(pk=may_contain_id)
        self.parts = []
        for p, q in pqs:
            self.parts.append(ItemsTreePart(p, q))
    
    def __getattr__(self, name):
        return getattr(self._mc, name)

class ItemsTreeItem(object):
    def __init__(self, item_template, quantity, line_num, parts=None, serials=None, state=None, errors=None, in_group=None):
        self.item_template = item_template
        self.quantity = quantity
        self.line_num = line_num
        self.is_group = item_template.category.is_group
        self.in_group = in_group
        self.contents = []
        self.parts = []
        self.state = state or ''
        self.errors = []
        # at this view, we want all the errors together
        if errors:
            self.errors = reduce(lambda a,b: a+b, errors.values())
        if parts:
            for category_id, pqs in parts.items():
                self.parts.append(ItemsTreeCat(category_id, pqs))

    @property
    def htmlerrors(self):
        """ Format the errors for a html title="" attribute
        """
        return u'\n'.join(self.errors)

class ItemsTreeWidget(forms.widgets.Widget):
    def render(self, name, value, attrs=None):
        items = []
        contained = defaultdict(list)
        if value:
            for kv in value:
                in_group = kv.get('in_group', None)
                if in_group:
                    contained[in_group].append(ItemsTreeItem(**kv))
                    continue
                items.append(ItemsTreeItem(**kv))

            for it in items:
                if it.line_num in contained:
                    it.is_group = True
                    it.contents = contained.pop(it.line_num)

            if contained:
                logger.debug("Stray contents remaining: %r", contained)

        final_attrs = self.build_attrs(attrs)
        self.html_id = final_attrs.pop('id', name)
        context = {
            'name': name,
            'html_id': self.html_id,
            'items': items,
            'extra_attrs': mark_safe(flatatt(final_attrs)),
            'func_slug': self.html_id.replace("-","")
        }

        return mark_safe(render_to_string('po_wizard_treeitems.html', context))


class ItemsTreeField(forms.Field):
    widget = ItemsTreeWidget


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
                quantity
                serials
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

            ret['in_group'] = data.get('id_%s_in_group' % name, None)
            if ret['in_group']:
                ret['in_group'] = int(ret['in_group'])
            ret['parts'] = {}
            for mc in ret['item_template'].category.may_contain.all():
                pa = ret['parts'][mc.id] = []
                qtys = data.getlist('id_%s-%d_part_qty' %(name, mc.id), [])
                for dpart in data.getlist('id_%s-%d_parts' %(name, mc.id), []):
                    dpart_id = int(dpart)
                    dqty = int(qtys.pop(0) or '0')
                    pa.append((ItemTemplate.objects.get(pk=dpart_id, category=mc.category), dqty))
            return ret
        else:
            logger.debug("no data at ItemsGroupWidget.value_from_datadict () %r", data)
            return {}

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
            'in_group': value.get('in_group', ''),
            'extra_attrs': mark_safe(flatatt(final_attrs)),
            'func_slug': self.html_id.replace("-",""),

            'item_template': item_template,
            'igroups': igroups,
        }

        return mark_safe(render_to_string('po_wizard_itemgroups.html', context))

class ItemsGroupField(forms.Field):
    widget = ItemsGroupWidget

    @classmethod
    def post_validate(cls, value):
        """ Run the bundle validation algorithm and store out within `value`
        """
        item_template = value.get('item_template', None)
        if item_template:
            bundled_items = {}
            # sum up the quantity of items per category:
            for pvals in value.get('parts', {}).values():
                for part, qty in pvals:
                    cat_id = part.category_id
                    bundled_items[cat_id] = bundled_items.get(cat_id, 0) + int(qty)
            errors = item_template.validate_bundle(bundled_items.items(), flat=False)
            value['errors'] = errors
            if errors and '*' in errors:
                value['state'] = 'bad'
            elif errors:
                value['state'] = 'missing'
            else:
                value['state'] = 'ok'
        return True

class GroupMCat(StrAndUnicode):
    def __init__(self, mc_cat, value, html_id):
        self._mc_cat = mc_cat
        self.parent_html_id = html_id
        self.html_id = '%s-%d' %(html_id , mc_cat.id)
        self.contents = []
        if 'contents' in value:
            for c in value['contents']:
                if c['item_template'].category_id == mc_cat.category_id:
                    self.contents.append(c)

    def __unicode__(self):
        return unicode(self._mc_cat.category.name)

    @property
    def name(self):
        return self._mc_cat.category.name

    @property
    def cat_id(self):
        return self._mc_cat.category_id

class GroupTreeWidget(forms.widgets.Widget):
    def render(self, name, value, attrs=None):
        """ Plain render() will only yield the management form

            For the categories, please iterate over this widget
        """
        items = []
        if not value:
            return mark_safe(u'<!-- no value for GTW -->')
        assert 'item_template' in value, 'Strange value: %r' % value.keys()
        assert 'line_num' in value, 'Strange value: %r' % value.keys()

        final_attrs = self.build_attrs(attrs)
        self.html_id = final_attrs.pop('id', name)
        return mark_safe((u'<input type="hidden" name="%s_item_template" value="%s" %s />' + \
                u'<input type="hidden" name="%s_line_num" value="%s" />') % \
                (self.html_id, value['item_template'].id, flatatt(final_attrs),
                 self.html_id, value['line_num']))

    def subwidgets(self, name, value, attrs=None, choices=()):
        if not value:
            return

        assert 'item_template' in value, 'Strange value: %r' % value.keys()
        for mc_cat in value['item_template'].category.may_contain.all():
            yield GroupMCat(mc_cat, value, self.html_id)

    def value_from_datadict(self, data, files, name):
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
            # ret['parts'] = {}
            if 'add-groupped' in data:
                ret['add-groupped'] = data['add-groupped']
            return ret
        else:
            logger.debug("no data at GroupGroupWidget.value_from_datadict () %r", data)
            return {}

class GroupGroupField(forms.Field):
    widget = GroupTreeWidget


# eof
