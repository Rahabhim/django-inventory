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
        Then, render() calls _render_one() recursively, until the
        last group leve, where "leaf" content is rendered

        The template syntax is::
            {% group_recurse %}
                <h2> some content for each group</h2>
            {% group_leaf %}
                <table> the table of detailed entries </table>
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
    def __init__(self, grp_list, grp_leaf):
        super(GroupNode, self).__init__()
        self.grp_list = grp_list
        self.grp_leaf = grp_leaf

    def _render_group(self, group_level, rows_filter, context):
        if group_level + 1 >= len(context['groupped_results']):
            return
        group = context['groupped_results'][group_level+1]
        context.push()
        context['cur_group'] = group
        if group.get('group_by', False):
            for cur_row in filter(rows_filter, group['values']):
                # prepare context, render node
                context.push()
                context['cur_row'] = cur_row
                context['cur_grp_fields'] = context['groupped_fields'][str(group_level)]
                yield mark_safe('<div class="group">')
                yield self.grp_list.render(context)

                nrf = self._get_rows_filter(group['group_by'], cur_row)
                for y in self._render_group(group_level+1, nrf, context):
                    yield y

                yield mark_safe('</div>')
                context.pop()

        else:
            # leaf level, only render final results
            context.push()
            context['cur_results'] = filter(rows_filter, group['values'])
            yield self.grp_leaf.render(context)
            context.pop()

        context.pop()
        return

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
    grp_list = parser.parse(('group_leaf',))
    parser.delete_first_token()
    grp_leaf = parser.parse(('end_group_recurse',))
    parser.delete_first_token()
    return GroupNode(grp_list, grp_leaf)

#eof