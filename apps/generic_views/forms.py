from django import forms
from django.forms.util import flatatt
from django.utils import formats
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from django.utils.translation import ugettext as _
# from django.utils.encoding import force_unicode
from django.db import models
from ajax_select.fields import AutoCompleteSelectField
from ajax_select import get_lookup

import types

import settings
from tree_field import ModelTreeChoiceField
import datetime
import logging

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

def _read_only_bound_data(data, initial):
    return data

class _ROw_mixin:
    """ Read-only widget behavior
    """
    read_only = True

    def _has_changed(self, initial, data):
        if self.read_only:
            return False
        else:
            return super(_ROw_mixin, self)._has_changed(initial, data)

class DetailForeignWidget(_ROw_mixin, forms.widgets.Widget):
    """A widget displaying read-only values of ForeignKey and ManyToMany fields

        Unlike Select* widgets, it won't query the db for choices
    """

    def __init__(self, queryset=None, choices=None, *args, **kwargs):
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
        elif value and isinstance(self.choices, forms.models.ModelChoiceIterator):
            queryset = self.choices.queryset
            if hasattr(value, '__iter__'):
                objs = queryset.filter(pk__in=value)
            else:
                objs = [queryset.get(pk=value),]
        elif value and self.choices:
            # only works with choices, so far
            objs = []
            for k, v in self.choices:
                if k == value:
                    objs.append(v)
                    break
        else:
            objs = []

        ret = self._render_ret(objs)
        return mark_safe(u'<span%s>%s</span>' % (flatatt(final_attrs), ret))

    def _render_ret(self, objs):
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
        return ret

class DetailPlainForeignWidget(DetailForeignWidget):
    def _render_ret(self, objs):
        ret = ''
        for obj in objs:
            if ret:
                ret += '<br/>'
            ret += conditional_escape(unicode(obj))
        return ret

class DetailForm(forms.ModelForm):
    def __init__(self, extra_fields=None, *args, **kwargs):
        super(DetailForm, self).__init__(*args, **kwargs)
        if extra_fields:
            for extra_field in extra_fields:
                if 'name' in extra_field:
                    fname = extra_field['name']
                else:
                    fname = extra_field['field']
                    if fname.endswith('.all'):
                        fname = fname[:-4]
                result = return_attrib(self.instance, extra_field['field'])
                ekws = {}
                klass = None
                if 'label' in extra_field:
                    ekws['label'] = extra_field['label']
                if 'widget' in extra_field:
                    ekws['widget'] = extra_field['widget']
                elif self._meta.widgets and fname in self._meta.widgets:
                    ekws['widget'] = self._meta.widgets[fname]
                if 'kwargs' in extra_field:
                    ekws.update(extra_field['kwargs'])
                #TODO: Add others result types <=> Field types
                if isinstance(result, models.query.QuerySet):
                    klass = forms.ModelMultipleChoiceField
                    ekws['queryset'] = result
                elif hasattr(result, 'all'):
                    klass = forms.ModelMultipleChoiceField
                    ekws['queryset'] = result.all()
                elif isinstance(result, (basestring,)):
                    klass = forms.CharField
                    ekws['initial'] = result

                if klass is None:
                    raise TypeError("Cannot determine right field %s for a result of %s" % \
                                ( extra_field['field'], type(result)))
                self.fields[fname] = klass(**ekws)

        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.widgets.Select, forms.widgets.SelectMultiple)):
                self.fields[field_name].widget = DetailForeignWidget(
                    attrs=field.widget.attrs,
                    choices=field.choices,
                    queryset=getattr(field, 'queryset', None),
                )
                self.fields[field_name].help_text=''
            elif isinstance(field.widget, ColumnsDetailWidget):
                self.fields[field_name].help_text=''

class RModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(RModelForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            if getattr(field.widget, 'read_only', False):
                field.required = False
                # patch the function, so that it never uses data (not) supplied
                # at the POST request
                field.bound_data = _read_only_bound_data

    def _post_clean(self):
        if self.cleaned_data is not None:
            for name, field in self.fields.items():
                if name in self.cleaned_data and getattr(field.widget, 'read_only', False):
                    del self.cleaned_data[name]

        super(RModelForm, self)._post_clean()

def UnAutoCompleteField(fields, name, request, use_radio=False, choice_limit=10):
    """Converts an AutoCompleteSelectField back to a ModelChoiceField, if possible

        There is chances that an auto-complete field will have too little choices
        to make sense for AJAX (or the UI experience of it). So, find if that's
        the case and convert back to a simple selection.

        For that, we need the request object, because the queryset of the lookup
        may depend on the logged-in user etc.

        @param fields the dictionary of fields for a form. We need all of it because
                we will update the dict in-place
        @param name the name of the field in the dict
        @param use_radio if true, a RadioSelect will be used
        @param choice_limit count() of items below which we trigger the conversion
    """
    try:
        field = fields[name]
        assert isinstance(field, AutoCompleteSelectField), repr(field)
        lookup = get_lookup(field.channel)
        qry = lookup.get_query('', request)
        if not qry.query.can_filter():
            # if there is any limits (slicing) in the query, remove them
            # in order to get the real count
            qry = qry._clone()
            qry.query.clear_limits()
        if qry.count() < choice_limit:
            widget = None
            if use_radio:
                widget = forms.widgets.RadioSelect
            new_field = forms.ModelChoiceField(queryset=qry,
                    label=field.label, widget=widget,
                    required=field.required, help_text=field.help_text,
                    initial=field.initial)
            fields[name] = new_field
    except Exception:
        logging.getLogger('apps.generic_views').warning("Could not resolve autocomplete %s:", name, exc_info=True)

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
        """
            @param qargs optionally, a dict to be passed to callable querysets
        """
        qargs = kwargs.pop('qargs', {})
        super(FilterForm, self).__init__(*args, **kwargs)
        self.field_conditions = {}
        for list_filter in list_filters:
            if 'condition' in list_filter:
                self.field_conditions[list_filter['name']] = list_filter['condition']
            label = list_filter.get('title', list_filter['name']).title()
            if 'lookup_channel' in list_filter:
                self.fields[list_filter['name']] = AutoCompleteSelectField( \
                        list_filter['lookup_channel'], show_help_text=False, \
                        label=label, required=False)
            elif 'queryset' in list_filter:
                if callable(list_filter['queryset']):
                    qfn = list_filter['queryset']
                    queryset = qfn(form=self, **qargs)
                else:
                    queryset = list_filter['queryset']

                if 'tree_by_parent' in list_filter:
                    self.fields[list_filter['name']] = ModelTreeChoiceField( \
                        parent_name= list_filter['tree_by_parent'], \
                        queryset=queryset, label=label, \
                        required=False)
                else:
                    self.fields[list_filter['name']] = forms.ModelChoiceField( \
                        queryset=queryset, label=label, \
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
                    mfield = mmodel._meta.get_field(afield)
                    choices = mfield.choices
                    assert choices, "Model %s.%s does not have choices" %(amodel.afield)
                    # don't do insert, but copy the list!
                    choices = [('','*' )] + choices
                else:
                    raise TypeError("Invalid type for list_filters.choices: %s" % type(list_filter['choices']))
                self.fields[list_filter['name']] = forms.ChoiceField(choices=choices, label=label, required=False)
            else:
                self.fields[list_filter['name']] = forms.CharField(label=label, required=False)

    def _init_by_request(self, request):
        for name, cond in self.field_conditions.items():
            if not cond:
                continue
            if not cond(None, {'request': request, 'user': request.user}):
                del self.fields[name]
        for fname in self.fields:
            if isinstance(self.fields[fname], AutoCompleteSelectField):
                UnAutoCompleteField(self.fields, fname, request)

class InlineModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(InlineModelForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field, forms.IntegerField):
                field.widget.attrs['class'] = 'integer'
            elif isinstance(field, forms.DecimalField):
                field.widget.attrs['class'] = 'decimal'

    def as_table(self):
        "Returns this form rendered as HTML <td>s"
        return self._html_output(
            normal_row = u'<td %(html_class_attr)s>%(label)s%(errors)s%(field)s%(help_text)s</td>',
            error_row = u'%s',
            row_ender = u'</td>',
            help_text_html = u'<br /><span class="helptext">%s</span>',
            errors_on_separate_row = False)

class ColumnsDetailWidget(_ROw_mixin, forms.widgets.Widget):
    """Read-only values of ForeignKey or ManyToMany fields, with columns

        Unlike Select* widgets, it won't query the db for choices
    """
    columns = []
    order_by = False
    show_header = True
    blind_mode = False
    extra_filter = None
    date_fmt = formats.get_format('DATE_INPUT_FORMATS')[0]
    datetime_fmt = formats.get_format('DATETIME_INPUT_FORMATS')[0]

    def __init__(self, queryset=None, choices=(), *args, **kwargs):
        super(ColumnsDetailWidget, self).__init__(*args, **kwargs)
        self.queryset = queryset
        self.choices = choices # but don't render them to list
        self.attrs.setdefault('class', 'columns-detail')

    def render(self, name, value, attrs=None, choices=()):
        final_attrs = self.build_attrs(attrs, name=name)
        objs = None
        if isinstance(self.choices, forms.models.ModelChoiceIterator):
            # The ModelChoiceIterator is a *very* slow object, we must extract
            # its queryset and use it directly
            self.queryset = self.choices.queryset
            self.choices = ()

        if value and hasattr(value, '__iter__') and self.queryset is not None:
            objs = self.queryset.filter(pk__in=value)
            if self.order_by:
                objs = objs.order_by(self.order_by)
        elif self.blind_mode and self.queryset is not None:
            objs = self.queryset
            if self.extra_filter:
                if isinstance(self.extra_filter, dict):
                    objs = objs.filter(**self.extra_filter)
                elif isinstance(self.extra_filter, models.Q):
                    objs = objs.filter(self.extra_filter)
                else:
                    raise TypeError("Cannot filter by %s" %(type(self.extra_filter)))
            if self.order_by:
                objs = objs.order_by(self.order_by)
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

        ret = ['<table%s>' % flatatt(final_attrs),]
        first = True
        if self.show_header:
            ret.append('<thead><tr>')
            for c in self.columns:
                width = ''
                if 'width' in c:
                    width = ' width="%s"' % c['width']
                ret.append('\t<th%s>%s</th>\n' % (width, unicode(c['name'])))
            ret.append('</tr></thead>\n')
            first = False
        ret.append('<tbody>\n')

        for obj in objs:
            ret.append('\t<tr>')
            for c in self.columns:
                cell = '<td%s>%s</td>'
                width = ''
                if first and 'width' in c:
                    width = ' width="%s"' % c['width']
                if c.get('attribute', False):
                    val = return_attrib(obj, c['attribute'])
                elif 'format' in c:
                    ret.append(cell % (width, c['format'](obj)))
                    continue
                else:
                    # no attribute, this must be the unicode(obj)
                    val = obj
                    try:
                        cell = '<td%%s><a href="%s">%%s</a></td>' % obj.get_absolute_url()
                    except AttributeError:
                        pass

                if isinstance(val, datetime.date):
                    val = val.strftime(self.date_fmt)
                elif isinstance(val, datetime.datetime):
                    val = val.strftime(self.datetime_fmt)
                val = conditional_escape(unicode(val))
                ret.append(cell % (width, val))
            ret.append('</tr>\n')
        ret.append('</table>\n\n')

        return mark_safe(''.join(ret))

class ReadOnlyInput(_ROw_mixin, forms.widgets.Input):

    def build_attrs(self, extra_attrs=None, **kwargs):
        return super(ReadOnlyInput, self).build_attrs(extra_attrs=extra_attrs, disabled=True, **kwargs)

class ROModelChoiceField(forms.ModelChoiceField):
    widget = DetailForeignWidget

class ReadOnlyDateInput(_ROw_mixin, forms.widgets.DateInput):
    def build_attrs(self, extra_attrs=None, **kwargs):
        return super(ReadOnlyDateInput, self).build_attrs(extra_attrs=extra_attrs, disabled=True, **kwargs)

#eof
