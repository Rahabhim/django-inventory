from django import forms 
from django.template import TemplateSyntaxError, Library, \
                            VariableDoesNotExist, Node, Variable
from django.template.defaulttags import token_kwargs
from django.template.loader import get_template
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


class Field_For(Node):
    def __init__(self, field_name, read_only=False, extra_context=None, \
                template_name='generic_form_field.html',):
        self.field_name = field_name
        self.read_only = read_only
        self.extra_context = extra_context or {}
        self.template_name = template_name

    def render(self, context):
        template = get_template(self.template_name)
        if '.' in self.field_name:
            fldname = self.field_name
        else:
            fldname = 'form.' + self.field_name

        try:
            field = Variable(fldname).resolve(context)
        except VariableDoesNotExist:
            field = None

        if not field:
            # we tolerate missing fields, because we want view templates to be
            # re-used for several forms.
            return ''

        values = dict([(name, var.resolve(context)) for name, var
                       in self.extra_context.iteritems()])
        context.update(values)
        context['field'] = field
        if self.read_only:
            context['read_only'] = True
        try:
            return template.render(context)
        finally:
            context.pop()

@register.tag
def add_classes_to_form(parser, token):
    args = token.split_contents()
    return StylingNode(args[1])

@register.tag
def field_label_tag(parser, token):
    args = token.split_contents()
    return FieldLabel(*args)

@register.tag
def field_for(parser, token):
    args = token.split_contents()
    if len(args) < 2:
        raise TemplateSyntaxError("%r tag takes at least one argument: the field name " % args[0])
    field_name = args[1]
    args = args[2:]
    options = {}
    while args:
        option = args.pop(0)
        if option in options:
            raise TemplateSyntaxError('The %r option was specified more '
                                      'than once.' % option)
        if option == 'with':
            value = token_kwargs(args, parser, support_legacy=False)
            if not value:
                raise TemplateSyntaxError('"with" in field_for tag needs at least '
                                          'one keyword argument.')
            options['extra_context'] = value
        elif option == 'read_only':
            options['read_only'] = True
        else:
            raise TemplateSyntaxError('Unknown argument for field_for tag: %r.' % option)

    return Field_For(field_name, **options)

#eof
