from django import forms
from django.template import TemplateSyntaxError, Library, \
                            VariableDoesNotExist, Node, Variable
from django.conf import settings
from django.utils.html import conditional_escape

register = Library()


class StylingNode(Node):
    def __init__(self, form_name, *args, **kwargs):
        self.form_name = form_name

    def render(self, context):
        form = Variable(self.form_name).resolve(context)

        for field_name, field in form.fields.items():
            if isinstance(field.widget, forms.widgets.TextInput):
                field.widget.attrs['class'] = 'text_field'
            elif isinstance(field.widget, forms.widgets.PasswordInput):
                field.widget.attrs['class'] = 'text_field'
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs['class'] = 'text_area'

        context[self.form_name] = form
        return ''


class FieldLabel(Node):
    def __init__(self, tag_name, field_var_name, *args, **kwargs):
        self.field_var_name = field_var_name

    def render(self, context):
        field = Variable(self.field_var_name).resolve(context)
        attrs = {'class': 'label' }
        contents = conditional_escape(field.label) # reverse-engineer the field.label_tag()
        if field.field.required and not context.get('read_only', False): # Variable('read_only').resolve(context):
            attrs['class'] += ' required'
            contents += ' *'
        return field.label_tag(contents=contents, attrs=attrs)

@register.tag
def add_classes_to_form(parser, token):
    args = token.split_contents()
    return StylingNode(args[1])

@register.tag
def field_label_tag(parser, token):
    args = token.split_contents()
    return FieldLabel(*args)

#eof
