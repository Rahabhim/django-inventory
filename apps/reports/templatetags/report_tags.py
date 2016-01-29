import types

# from django.core.urlresolvers import reverse
from django.conf import settings
# from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.template import Library, Node, NodeList
from django.utils.translation import ugettext_lazy as _

register = Library()

def return_attrib(obj, attrib, arguments={}):
    try:
        if isinstance(attrib,basestring) and attrib.startswith('+'):
            attrib = attrib[1:]
        if isinstance(obj, dict):
            return obj.get(attrib, None)
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

    def _render_group(self, cur_group, data, context):
        context.push()
        context['cur_group'] = cur_group
        for k, v in cur_group.items():
            context[k] = v

        if cur_group.get('sub_group'):
            context['do_group_recurse'] = lambda: self._render_group_flat( cur_group['sub_group'], context)
        else:
            context['do_group_recurse'] = lambda: ''
        context['cur_results'] = data
        context['get_rowspan'] = lambda: context['cur_row'].get('_rowspan', 1)
        context['has_sub_values'] = lambda: bool(context['cur_row'].get('_sub_values'))
        yield self.grp_list.render(context)
        context.pop()
        return

    def _render_group_flat(self, cur_group, context):
        nodelist = NodeList()
        for res in self._render_group(cur_group, context['cur_row'].get('_sub_values'), context):
            nodelist.append(res)
        return nodelist.render(context)

    def _get_rows_filter(self, group_by, cur_row):
        sample = {}
        for f in group_by:
            sample[f] = cur_row.get(f, None)

        def rfilter(row):
            for k, v in sample.items():
                if row.get(k, None) != v:
                    return False
            return True
        return rfilter

    def _pre_calc_fields(self, context, group_level=0):
        res = {}
        results = context['groupped_results'][1:]
        res = None
        in_table = False
        while results:
            cur_results = results.pop()
            if cur_results and cur_results.get('group_by'):
                level = cur_results['group_level']
                cur_grp_fields = context['groupped_fields'].get(str(level-1), [{},])
                g = {'group_level': level,
                    'group_by': cur_results['group_by'],
                    'group_mode': cur_grp_fields[0].get('group_mode', 'row'),
                    'sub_group': res,
                    'in_table': in_table,
                    }
                if g['group_mode'] == 'table':
                    l = cur_grp_fields[:]
                    l.sort(key=lambda fc: fc.get('sequence'))
                    l.append({'id': '_count', 'name': _("Count"), 'widget': ''})
                    g['field_cols'] = []
                    g['render_head'] = []
                    for f in l:
                        if 'id' not in f:
                            continue
                        g['field_cols'].append({'id': f['id'], 'widget': f['widget']})
                        g['render_head'].append({'id': f['id'], 'name': f['name']})
                    in_table = True

                elif g['group_mode'] == 'row':
                    l = cur_grp_fields[:]
                    l.sort(key=lambda fc: fc.get('sequence'))
                    # l.append({'id': '_count', 'name': False, 'widget': ''})
                    g['field_cols'] = []
                    for f in l:
                        if 'id' not in f:
                            continue
                        g['field_cols'].append({'id': f['id'], 'widget': f['widget'], 'name': f['name']})
                    g['render_head'] = [{'name': '-'}]
                    in_table = False

                elif g['group_mode'] == 'left_col':
                    col0 = {'id': False, 'name': cur_grp_fields[0]['name']}
                    if res:
                        g['render_head'] = res.pop('render_head')
                        res['render_head'] = False
                    else:
                        g['render_head'] = []
                    g['render_head'].insert(0, col0)
                    l = cur_grp_fields[:]
                    l.sort(key=lambda fc: fc.get('sequence'))
                    g['field_cols'] = []
                    for f in l:
                        if 'id' not in f:
                            continue
                        c = {'id': f['id'], 'widget': f['widget']}
                        if f is not cur_grp_fields[0]:
                            c['name'] = f['name']
                        g['field_cols'].append(c)
                    in_table = True
                else:
                    raise ValueError("unknown group mode: %s" % g['group_mode'])
            elif cur_results:
                # detailed results
                fc = context['field_cols']
                g = {'group_level': cur_results['group_level'],
                    'field_cols': [],
                    'render_head': [],
                    'group_by': False, 'group_mode': False }
                for f in fc:
                    if 'id' not in f:
                        continue
                    g['field_cols'].append({'id': f['id'], 'widget': f['widget']})
                    g['render_head'].append({'id': f['id'], 'name': f['name']})
            # unshift stack:
            res = g

        return res

    def _pre_calc_data(self, context, fields):
        """ Convert set of flat results lists to a nested tree

            @param fields nested fields definitions, result of `_pre_calc_fields()`
        """
        rowspan_getter = lambda srow: srow.get('_rowspan', 1)

        if fields['group_by'] and fields['sub_group']:
            ivals = []
            group_by = fields['group_by']
            for row in context['groupped_results'][fields['group_level']].pop('values'):
                ivals.append((self._get_rows_filter(group_by, row), row))
                row['_sub_values'] = [] # after rows filter!

            for sub_row in self._pre_calc_data(context, fields['sub_group']):
                for fn, row in ivals:
                    if fn(sub_row):
                        row['_sub_values'].append(sub_row)
                        break
                else:
                    raise RuntimeError("value not belonging to any group: %r" % sub_row)

            if fields['group_mode'] == 'table':
                for fn, row in ivals:
                    if row['_sub_values']:
                        row['_rowspan'] = 2
            elif fields['group_mode'] == 'left_col':
                for fn, row in ivals:
                    row['_rowspan'] = sum(map(rowspan_getter, row['_sub_values'])) + 1

            return [row for fn, row in ivals]
        else:
            # no more levels to process
            return context['groupped_results'][fields['group_level']].pop('values')

    def render(self, context):
        nodelist = NodeList()
        context.push()
        cur_group = self._pre_calc_fields(context)
        data = self._pre_calc_data(context, cur_group)

        for res in self._render_group(cur_group, data, context):
           nodelist.append(res)
        context.pop()
        return nodelist.render(context)

@register.tag
def group_recurse(parser, token):
    grp_list = parser.parse(('end_group_recurse',))
    parser.delete_first_token()
    return GroupNode(grp_list)

#eof