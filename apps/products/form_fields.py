# -*- encoding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import StrAndUnicode, force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.forms.util import flatatt
from django.utils.datastructures import MultiValueDict, MergeDict

from models import ProductAttributeValue

class CSWItem(StrAndUnicode):
    """ItemCategory record for the CategoriesSelectWidget
    
        The widget will display all available categories. While building the
        html code, this pseydo-object will represent each Category record to
        be rendered.
    """

    def __init__(self, parent, obj):
        self._parent = parent
        self._obj = obj

    def __unicode__(self):
        return unicode(self._obj)

    @property
    def did(self):
        """div-id of this selection element
        """
        return mark_safe("%s-%d" %(self._parent._name, self._obj.id))

    @property
    def id(self):
        """Record-id (aka. value) for this item
        """
        return mark_safe(str(self._obj.id))

    @property
    def name(self):
        """ID of the parent field
        """
        return self._parent._name

    @property
    def picture(self):
        return self._obj.picture

class CSWItem_Main(CSWItem):
    """Instance of first-level category in the page
    
        It can be iterated to find 2nd level categories
    """
    def standalones(self):
        """Returns non-bundled sub-categories
        """
        for subcat in self._parent._queryset.filter(parent=self._obj, ):
            yield CSWItem_Sub(self._parent, subcat)

class CSWItem_Sub(CSWItem):
    """Instance of second-level category
    """
    pass

class CSWRenderer(StrAndUnicode):
    # parent_field = 'parent'

    def __init__(self, queryset, name, value, attrs):
        self._queryset = queryset
        self._name = name
        self._value = value or []
        self.attrs = attrs

    def __unicode__(self):
        return "<!-- CSWRenderer: %s with %d vals -->" % (self._name, len(self._value))

    def __iter__(self):
        for icat in self._queryset.filter(parent__isnull=True):
            yield CSWItem_Main(self, icat)

    def render(self):
        return mark_safe(unicode(self))

class CategoriesSelectWidget(forms.widgets.Select):
    """Select widget of ItemCategory entries, in 3-level selectors

        @param queryset must be the full dataset of *all three* levels
            of item categories to use. It will be filter()ed accordingly
            for each level
    """

    def __init__(self, queryset=None, choices=(), *args, **kwargs):
        super(CategoriesSelectWidget, self).__init__(*args, **kwargs)
        self.queryset = queryset
        self.choices = choices # but don't render them to list
        self._renderer = None

    def subwidgets(self, name, value, attrs=None, choices=()):
        for w in self.get_renderer(name, value, attrs, choices):
            yield w

    def render(self, name, value, attrs=None, choices=()):
        return self.get_renderer(name, value, attrs, choices).render()

    def get_renderer(self, name, value, attrs=None, choices=()):
        """ Rendering of this widget MUST be done with some template loops

            We do NOT support direct text rendering like `{{ this_field }}`, but
            instead mandate a loop like `{% for cat1 in this_field %} {{ cat1.title }}`
        """
        if not self._renderer:
            final_attrs = self.build_attrs(attrs, name=name)
            if isinstance(self.choices, forms.models.ModelChoiceIterator):
                # The ModelChoiceIterator is a *very* slow object, we must extract
                # its queryset and use it directly
                self.queryset = self.choices.queryset
                self.choices = ()
            self._renderer = CSWRenderer(self.queryset, name, value, final_attrs)
        return self._renderer

class CATItem(StrAndUnicode):
    """Product Attribute selection

        This will display a combo box with values for one Attribute applicable
        to some product of a specific category.
    """

    def __init__(self, parent_name, cattr, values):
        """
            @param parent the widget
            @param cattr the category attribute
        """
        self._parent_name = parent_name
        self._label_name = cattr.name
        self._attr_id = cattr.id
        self._is_required = cattr.required
        self._values = []
        for v in cattr.values.all():
            self._values.append((v.id, v.value, bool(v.id in values)))

    def _make_label(self):
        return u'<label for="%s">%s</label>'  % (self.did, self._label_name)

    def __unicode__(self):
        """returns the full option element
        """
        return self._make_label() + self.option

    @property
    def did(self):
        """div-id of this selection element
        """
        return mark_safe("%s-a%d" %(self._parent_name, self._attr_id))

    @property
    def name(self):
        """ID of the parent field
        """
        return self._parent_name

    @property
    def label(self):
        """ The label to display by the option
        """
        return mark_safe(self._make_label())

    @property
    def option(self):
        ret = []
        ret.append(u'<select id="%s" name="%s">' % (self.did, self._parent_name))
        ret.append(u'<option value="">-------</option>')
        for vid, label, selected in self._values:
            ret.append(u'<option value="%d"%s>%s</option>' % (
                    vid, selected and ' selected="selected"' or '',
                    conditional_escape(force_unicode(label)) ))
        ret.append(u'</select>')
        return u' '.join(ret)

class CategoriesAttributesWidget(forms.widgets.Widget):
    def __init__(self, queryset=None, choices=(), *args, **kwargs):
        super(CategoriesAttributesWidget, self).__init__(*args, **kwargs)
        self.queryset = queryset
        self.choices = choices # but don't render them to list

    def subwidgets(self, name, value, attrs=None, choices=()):
        if not (value and ('from_category' in value)):
            return
        for cattr in value['from_category'].attributes.all():
            yield CATItem(name, cattr, value.get('all', []))

    def render(self, name, value, attrs=None, choices=()):
        final_attrs = self.build_attrs(attrs, name=name)
        
        ret = []
        ret.append(u'<div%s>' % flatatt(final_attrs))
        for sw in self.subwidgets(name, value, attrs):
            ret.append( unicode(sw))
        ret.append('</div>')
        return mark_safe(u' '.join(ret))


    def value_from_datadict(self, data, files, name):
        """
        Given a dictionary of data and this widget's name, returns the value
        of this widget. Returns None if it's not provided.
        """
        if isinstance(data, (MultiValueDict, MergeDict)):
            return data.getlist(name)
        return data.get(name, None)

    def _has_changed(self, initial, data): # TODO
        if initial is None:
            initial = []
        if data is None:
            data = []
        if len(initial) != len(data):
            return True
        initial_set = set([force_unicode(value) for value in initial])
        data_set = set([force_unicode(value) for value in data])
        return data_set != initial_set


class CategoriesAttributesField(forms.Field):
    widget = CategoriesAttributesWidget
    default_error_messages = {
        'invalid_category': _("Attribute %(attribute)s does not apply to category %(category)s"),
        'duplicate_attribute': _("Attribute %(attribute)s specified twice"),
        'missing_attribute': _("Attribute %(attribute)s is required for %(category)s"),
        'missing_attributes': _("Attributes %(attributes)s are required for %(category)s"),
        }

    def to_python(self, value):
        return filter(bool, value)

    def bound_data(self, data, initial):
        if initial:
            ret = initial.copy()
        else:
            ret = {}
        if data:
            ret['all'] = data
        return ret

    def validate(self, value):
        # tolerate empty values, we will check at post_clean()
        return True

    def post_clean(self, instance, cleaned_data):
        """ Cleanup of 'attributes' in cleaned_data, according to `instance.category`
        
            We have to obey the rules of attributes for the item's category, ie.
            force those attributes required, reject ones that do not apply to the
            category
        """
        if not instance.pk:
            return
        orig_aval_ids = map(int, cleaned_data.pop('attributes', []))
        attribs = {}
        for id, required, name in instance.category.attributes.values_list('id', 'required', 'name'):
            attribs[id] = {'name': name, 'required': required }
        clean_attribs = []

        for aval in ProductAttributeValue.objects.filter(id__in=orig_aval_ids):
            if aval.atype.applies_category_id != instance.category_id:
                raise forms.ValidationError(self.error_messages['invalid_category'] % \
                        {'attribute': aval.atype.name, 'category': unicode(instance.category)})
            found = attribs.pop(aval.atype_id, None)
            if not found:
                raise forms.ValidationError(self.error_messages['duplicate_attribute'] % \
                        {'attribute': aval.atype.name})
            clean_attribs.append(aval.id)
        
        for key in attribs.keys():
            if not attribs[key]['required']:
                attribs.pop(key)

        if attribs:
            if len(attribs) > 1:
                raise forms.ValidationError(self.error_messages['missing_attributes'] % \
                            { 'category': unicode(instance.category),
                                'attributes': ', '.join([a['name'] for a in attribs.values()]) })
            else:
                raise forms.ValidationError(self.error_messages['missing_attribute'] % \
                            { 'category': unicode(instance.category),
                                'attribute': attribs.values()[0]['name'] })
        
        cleaned_data['attributes'] = clean_attribs

#eof
