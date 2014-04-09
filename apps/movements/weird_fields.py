# -*- encoding: utf-8 -*-
import logging
from collections import defaultdict
from django.utils.translation import ugettext_lazy as _

from django import forms
from django.template.loader import render_to_string
from django.utils.encoding import StrAndUnicode
from django.utils.safestring import mark_safe
from django.db.models import Count
from generic_views.forms import DetailForeignWidget
from django.forms.util import flatatt
from django.conf import settings

from products.models import Manufacturer, ItemTemplate, ItemCategoryContain
from products.form_fields import CATItem
from ajax_select import get_lookup
from ajax_select.fields import _check_can_add, bootstrap, plugin_options

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
                if not kv['item_template']:
                    continue
                in_group = kv.get('in_group', None)
                if kv['item_template'].category.is_group:
                    # reset the errors, because the earlier stage couldn't
                    # have computed the contects correctly
                    kv['errors'] = defaultdict(list)
                    kv['state'] = 'ok'
                if in_group:
                    contained[in_group].append(ItemsTreeItem(**kv))
                    continue
                items.append(ItemsTreeItem(**kv))

            for it in items:
                gcontents = []
                if it.line_num in contained:
                    it.is_group = True
                    it.contents = contained.pop(it.line_num)
                    gcontents = [ (ic.item_template.category_id, ic.quantity) for ic in it.contents]
                new_errors = it.item_template.validate_bundle(gcontents,flat=True, group_mode=True)
                if new_errors:
                    it.errors += new_errors
                    it.state = 'bad'

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
        return Manufacturer.objects.filter(products__category=self._obj.category)\
                .annotate(num_products=Count('products')).order_by('name')

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
    _template_name = 'po_wizard_itemgroups.html'

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

            ret['in_group'] = data.get('id_%s_in_group' % name, None)
            if ret['in_group']:
                ret['in_group'] = int(ret['in_group'])
            ret['parts'] = {}
            for mc in ret['item_template'].category.may_contain.all():
                pa = ret['parts'][mc.id] = []
                qtys = data.getlist('id_%s-%d_part_qty' %(name, mc.id), [])
                for dpart in data.getlist('id_%s-%d_parts' %(name, mc.id), []):
                    if not qtys:
                        break
                    if not dpart:
                        continue
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
            'line_num': value.get('line_num', None) or '',
            'in_group': value.get('in_group', None) or '',
            'extra_attrs': mark_safe(flatatt(final_attrs)),
            'func_slug': self.html_id.replace("-",""),

            'item_template': item_template,
            'igroups': igroups,
        }

        return mark_safe(render_to_string(self._template_name, context))

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

class Step5ChoiceWidget(forms.widgets.RadioSelect):
    def render(self, name, value, attrs=None):
        """ Expand locations according to our queryset and then render by template
        """
        if not value:
            return mark_safe(u'<!-- no value for Step5ChoiceWidget -->')

        final_attrs = self.build_attrs(attrs)
        self.html_id = final_attrs.pop('id', name)
        value, rdict = value

        context = {'name': name,
                'html_id': self.html_id,
                'extra_attrs': mark_safe(flatatt(final_attrs)),
                'func_slug': self.html_id.replace("-",""),
                'auto_items': [],
                'choices': self.choices,
                }

        for ltmpl_id, items in rdict.items():
            if ltmpl_id == '*':
                context['choices_iter'] = self.subwidgets(name, value)
                context['misc_items'] = items
            else:
                loc = self.choices.queryset.filter(template_id=ltmpl_id).all()[:1]
                context['auto_items'].append((loc, items))

        if 'misc_items' not in context:
            for d in self.choices:
                context['default_choice'] = d[0]
                break

        return mark_safe(render_to_string('po_wizard_step5_locations.html', context))

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        rdict = data.get(name+'s', None)
        return value, rdict

class Step5ChoiceField(forms.ModelChoiceField):
    widget = Step5ChoiceWidget

    def valid_value(self, value):
        return True

    def to_python(self, value):
        if isinstance(value, tuple):
            value = value[0]
        return super(Step5ChoiceField,self).to_python(value)

# -----------------------
class AcSelectMultipleWidget(forms.widgets.SelectMultiple):
    """ widget to select multiple models, fork of AutoCompleteSelectMultipleField """

    add_link = None
    render_template = 'autocompleteselectmultiple.html'

    def __init__(self,
                 channel,
                 help_text='',
                 show_help_text=True,
                 plugin_options = {},
                 *args, **kwargs):
        super(AcSelectMultipleWidget, self).__init__(*args, **kwargs)
        self.channel = channel

        self.help_text = help_text
        self.show_help_text = show_help_text
        self.plugin_options = plugin_options

    def render(self, name, value, attrs=None):

        if value is None:
            value = []

        final_attrs = self.build_attrs(attrs)
        self.html_id = final_attrs.pop('id', name)

        lookup = get_lookup(self.channel)

        # eg. value = [3002L, 1194L]
        if value:
            current_ids = "|" + "|".join( str(pk) for pk in value ) + "|" # |pk|pk| of current
        else:
            current_ids = "|"

        objects = lookup.get_objects(value)

        # text repr of currently selected items
        initial = [ [obj.pk, lookup.get_result(obj), lookup.format_item_display(obj)] \
                        for obj in objects]

        if self.show_help_text:
            help_text = self.help_text
        else:
            help_text = u''

        context = {
            'name':name,
            'html_id':self.html_id,
            'current':value,
            'current_ids':current_ids,
            'current_codes': [ lookup.get_result(obj) for obj in objects],
            # 'current_reprs':mark_safe(simplejson.dumps(initial)),
            'help_text':help_text,
            'extra_attrs': mark_safe(flatatt(final_attrs)),
            'func_slug': self.html_id.replace("-",""),
            'add_link' : self.add_link,
        }
        context.update(plugin_options(lookup,self.channel,self.plugin_options,initial))
        context.update(bootstrap())

        return mark_safe(render_to_string(self.render_template, context))

    def value_from_datadict(self, data, files, name):
        # eg. u'members': [u'|229|4688|190|']
        return [long(val) for val in data.get(name,'').split('|') if val]

    def id_for_label(self, id_):
        return '%s_text' % id_


class AcSelectMultipleField(forms.fields.CharField):

    """ form field to select multiple models for a ManyToMany db field """

    channel = None
    widget_class = AcSelectMultipleWidget

    def __init__(self, channel, *args, **kwargs):
        self.channel = channel

        help_text = kwargs.get('help_text')
        show_help_text = kwargs.pop('show_help_text',False)

        if not (help_text is None):
            # '' will cause translation to fail
            # should be u''
            if type(help_text) == str:
                help_text = unicode(help_text)
            # django admin appends "Hold down "Control",..." to the help text
            # regardless of which widget is used. so even when you specify an explicit help text it appends this other default text onto the end.
            # This monkey patches the help text to remove that
            if help_text != u'':
                if type(help_text) != unicode:
                    # ideally this could check request.LANGUAGE_CODE
                    translated = help_text.translate(settings.LANGUAGE_CODE)
                else:
                    translated = help_text
                django_default_help = _(u'Hold down "Control", or "Command" on a Mac, to select more than one.').translate(settings.LANGUAGE_CODE)
                if django_default_help in translated:
                    cleaned_help = translated.replace(django_default_help,'').strip()
                    # probably will not show up in translations
                    if cleaned_help:
                        help_text = cleaned_help
                    else:
                        help_text = u""
                        show_help_text = False
        else:
            show_help_text = False
            help_text = None

        # django admin will also show help text outside of the display
        # area of the widget.  this results in duplicated help.
        # it should just let the widget do the rendering
        # so by default do not show it in widget
        # if using in a normal form then set to True when creating the field
        widget_kwargs = {
            'channel': channel,
            'help_text': help_text,
            'show_help_text': show_help_text,
            'plugin_options': kwargs.pop('plugin_options',{})
        }
        kwargs['widget'] = self.widget_class(**widget_kwargs)
        kwargs['help_text'] = help_text

        super(AcSelectMultipleField, self).__init__(*args, **kwargs)

    def clean(self, value):
        if not value and self.required:
            raise forms.ValidationError(self.error_messages['required'])
        return value # a list of IDs from widget value_from_datadict

    def check_can_add(self,user,model):
        _check_can_add(self,user,model)

class DeptSelectWidget(AcSelectMultipleWidget):
    render_template = 'depts_select_multiple.html'

class DeptSelectMultipleField(AcSelectMultipleField):
    widget_class = DeptSelectWidget

# eof
