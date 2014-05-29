import types

from django.core.urlresolvers import reverse
from django.conf import settings
from django.template.defaultfilters import stringfilter
from django.template import Library, Node, Variable


register = Library()

def return_attrib(obj, attrib, arguments={}):
    try:
        if isinstance(obj, dict):
            return obj[attrib]
        elif isinstance(attrib, types.FunctionType):
            return attrib(obj)
        else:
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
            return "Error: %s; %s" % (attrib, err)
        else:
            pass

@register.filter
def attrib(value, arg):
    return return_attrib(value, arg)

@register.filter
def dvalue(value, arg):
    arg = arg.replace('.', '__')
    return return_attrib(value, arg)

#eof