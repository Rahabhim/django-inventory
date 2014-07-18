import types

# from django.core.urlresolvers import reverse
from django.conf import settings
# from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.template import Library, Node, NodeList


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
    # arg = arg.replace('.', '__')
    return return_attrib(value, arg)


class GroupNode(Node):
    """ Renderer for recursive group levels

        We only compile this once, no recursive inclusions.

        The template syntax is::
            {% group_recurse %}
                {% for cur_row in rows %}
                    <h2> some content for each group</h2>
                    {{ do_group_recurse }}
                {% endfor %}
            {% end_group_recurse %}

        Which shall render as::

            <div class="group">
                <h2>First group level</h2>
                <div class="group">
                    <h2>Second group level</h2>
                    <table> Entries...</table>
                </div>
            </div>
    """
    def __init__(self, grp_list):
        super(GroupNode, self).__init__()
        self.grp_list = grp_list

    def _render_group(self, group_level, rows_filter, context):
        if group_level + 1 >= len(context['groupped_results']):
            return
        group = context['groupped_results'][group_level+1]
        context.push()
        context['cur_group'] = group
        grp_fields = context['groupped_fields'].get(str(group_level), [])
        context['cur_grp_fields'] = grp_fields
        context['do_group_recurse'] = lambda: self._render_group_flat(group_level+1, context)
        context['cur_results'] = filter(rows_filter, group['values'])
        yield self.grp_list.render(context)
        context.pop()
        return

    def _render_group_flat(self, group_level, context):
        nodelist = NodeList()
        nrf = self._get_rows_filter(context['cur_group']['group_by'], context['cur_row'])
        for res in self._render_group(group_level, nrf, context):
            nodelist.append(res)
        return nodelist.render(context)

    def _get_rows_filter(self, group_by, cur_row):
        sample = {}
        for f in group_by:
            sample[f] = cur_row.get(f, False)

        def rfilter(row):
            for k, v in sample.items():
                if row.get(k, None) != v:
                    return False
            return True
        return rfilter

    def render(self, context):
        nodelist = NodeList()
        context.push()
        for res in self._render_group(0, lambda row: True, context):
            nodelist.append(res)
        context.pop()
        return nodelist.render(context)

@register.tag
def group_recurse(parser, token):
    grp_list = parser.parse(('end_group_recurse',))
    parser.delete_first_token()
    return GroupNode(grp_list)

#eof