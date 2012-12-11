from django.template import Library, Node, Variable, VariableDoesNotExist
from django.utils.translation import ugettext as _
from copy import copy

register = Library()


def filter_form(context):
    new_context = copy(context)

    new_context.update({
        'form':context['filter_form'],
        'submit_method':'get',
        'title':_(u'Filter'),
    })
    return new_context
register.inclusion_tag('filter_form_subtemplate.html', takes_context=True)(filter_form)

#eof