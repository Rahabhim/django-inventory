from django import forms
from django.forms.util import flatatt
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from django.utils.translation import ugettext as _
from django.utils.encoding import force_unicode
from django.db import models
from ajax_select.fields import AutoCompleteSelectField

import types

import settings

def return_attrib(obj, attrib, arguments=None):
    try:
        result = reduce(getattr, attrib.split("."), obj)
        if isinstance(result, types.MethodType):
            if arguments:
                return result(**arguments)
            else:
                return result()
        else:
            return result
    except Exception, err:
        if settings.DEBUG:
            return "Attribute error: %s; %s" % (attrib, err)
        else:
            pass


class DetailSelectMultiple(forms.widgets.SelectMultiple):
    def __init__(self, queryset=None, *args, **kwargs):
        self.queryset=queryset
        super(DetailSelectMultiple, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = ''
        #final_attrs = self.build_attrs(attrs, name=name)
        output = u'<ul class="list">'
        options = None
        if value:
            if getattr(value, '__iter__', None):
                options = [(index, string) for index, string in self.choices if index in value]
            else:
                options = [(index, string) for index, string in self.choices if index == value]
        else:
            if self.choices:
                if self.choices[0] != (u'', u'---------') and value != []:
                    options = [(index, string) for index, string in self.choices]

        if options:
            for index, string in options:
                if self.queryset is not None:
                    try:
                        output += u'<li><a href="%s">%s</a></li>' % (self.queryset.get(pk=index).get_absolute_url(), string)
                    except AttributeError:
                        output += u'<li>%s</li>' % (string)
                else:
                    output += u'<li>%s</li>' % string
        else:
            output += u'<li>%s</li>' % _(u"None")
        return mark_safe(output + u'</ul>\n')

class DetailForeignWidget(forms.widgets.Widget):
    """A widget displaying read-only values of ForeignKey and ManyToMany fields

        Unlike Select* widgets, it won't query the db for choices
    """
    def __init__(self, queryset=None, choices=(), *args, **kwargs):
        super(DetailForeignWidget, self).__init__(*args, **kwargs)
        self.queryset = queryset
        self.choices = choices # but don't render them to list

    def render(self, name, value, attrs=None, choices=()):
        final_attrs = self.build_attrs(attrs, name=name)
        objs = None
        if value and hasattr(value, '__iter__') and self.queryset is not None:
            objs = self.queryset.filter(pk__in=value)
        elif value and self.queryset is not None:
            objs = [self.queryset.get(pk=value),]
        elif value and self.choices:
            # only works with choices, so far
            objs = []
            for k, v in self.choices:
                if k == value:
                    objs.append(v)
                    break
        else:
            objs = []

        ret = ''
        for obj in objs:
            href = None
            if ret:
                ret += '<br/>'
            try:
                href = obj.get_absolute_url()
                ret += '<a href="%s">' % href
            except AttributeError:
                href = None

            ret += conditional_escape(unicode(obj))
            if href is not None:
                ret += '</a>'

        return mark_safe(u'<span%s>%s</span>' % (flatatt(final_attrs), ret))

class DetailForm(forms.ModelForm):
    def __init__(self, extra_fields=None, *args, **kwargs):
        super(DetailForm, self).__init__(*args, **kwargs)
        if extra_fields:
            for extra_field in extra_fields:
                result = return_attrib(self.instance, extra_field['field'])
                label = 'label' in extra_field and extra_field['label'] or None
                #TODO: Add others result types <=> Field types
                if isinstance(result, models.query.QuerySet):
                    self.fields[extra_field['field']]=forms.ModelMultipleChoiceField(queryset=result, label=label)

        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.widgets.Select, forms.widgets.SelectMultiple)):
                self.fields[field_name].widget = DetailForeignWidget(
                    attrs=field.widget.attrs,
                    choices=field.choices,
                    queryset=getattr(field, 'queryset', None),
                )
                self.fields[field_name].help_text=''


class GenericConfirmForm(forms.Form):
    pass


class GenericAssignRemoveForm(forms.Form):
    left_list = forms.ModelMultipleChoiceField(required=False, queryset=None)
    right_list = forms.ModelMultipleChoiceField(required=False, queryset=None)
    def __init__(self, left_list_qryset=None, right_list_qryset=None, left_filter=None, *args, **kwargs):
        super(GenericAssignRemoveForm, self).__init__(*args, **kwargs)
        if left_filter:
            self.fields['left_list'].queryset = left_list_qryset.filter(*left_filter)
        else:
            self.fields['left_list'].queryset = left_list_qryset

        self.fields['right_list'].queryset = right_list_qryset


class FilterForm(forms.Form):
    def __init__(self, list_filters, *args, **kwargs):
        super(FilterForm, self).__init__(*args, **kwargs)
        for list_filter in list_filters:
            label = list_filter.get('title', list_filter['name']).title()
            if 'lookup_channel' in list_filter:
                self.fields[list_filter['name']] = AutoCompleteSelectField( \
                        list_filter['lookup_channel'], label=label, required=False)
            elif 'queryset' in list_filter:
                self.fields[list_filter['name']] = forms.ModelChoiceField( \
                        queryset=list_filter['queryset'], label=label, \
                        required=False)
            elif 'choices' in list_filter:
                if isinstance(list_filter['choices'], tuple):
                    choices = list_filter['choices']
                elif isinstance(list_filter['choices'], basestring):
                    # we also support the "app.model.field" syntax to automatically fetch
                    # the choices for some model field
                    aapp, amodel, afield = list_filter['choices'].rsplit('.', 2)
                    mmodel = models.get_model(aapp, amodel)
                    assert mmodel, "Model not found: %s.%s" %(aapp, amodel)
                    choices = mmodel._meta.get_field(afield).choices
                    assert choices, "Model %s.%s does not have choices" %(amodel.afield)
                    # don't do insert, but copy the list!
                    choices = [('','---')] + choices
                else:
                    raise TypeError("Invalid type for list_filters.choices: %s" % type(list_filter['choices']))
                self.fields[list_filter['name']] = forms.ChoiceField(choices=choices, label=label, required=False)
            else:
                self.fields[list_filter['name']] = forms.CharField(label=label, required=False)

class InlineModelForm(forms.ModelForm):
    def as_table(self):
        "Returns this form rendered as HTML <td>s"
        return self._html_output(
            normal_row = u'<td %(html_class_attr)s>%(label)s%(errors)s%(field)s%(help_text)s</td>',
            error_row = u'%s',
            row_ender = u'</td>',
            help_text_html = u'<br /><span class="helptext">%s</span>',
            errors_on_separate_row = False)

#eof
