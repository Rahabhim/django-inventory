# -*- encoding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseNotFound, HttpResponse, HttpResponseNotAllowed
from django.core.urlresolvers import reverse
from django.utils.functional import Promise
from django.db import models
from django.db.models.query import QuerySet
import json
from django.utils.safestring import SafeString
from collections import defaultdict

from models import SavedReport
from common.api import user_is_staff

class JsonEncoderS(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return unicode(obj)
        elif isinstance(obj, QuerySet):
            return list(obj)
        return super(JsonEncoderS, self).default(obj)

# ----------- Filters ----------------

class CJFilter(object):
    """Base for some search criterion, represents a search field
    """
    title = ''
    _instances = []
    sequence = 10

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        CJFilter._instances.append(self)

    def __repr__(self):
        return "<%s >" % self.__class__.__name__

    def real_init(self):
        pass

    def getGrammar(self):
        return {'name': self.title, 'sequence': self.sequence }

    def getQuery(self, request, name, domain):
        """Constructs a Django Q object, according to `domain` (as from client)

            @param name field name
        """
        raise NotImplementedError(self.__class__.__name__)

    def to_main_report(self, idn):
        ret = {'id': idn, 'name': self.title, 'sequence': self.sequence }
        if getattr(self, 'famfam_icon', None):
            ret['famfam'] = 'famfam-' + self.famfam_icon

        return ret

    def getResults(self, request, **kwargs):
        raise NotImplementedError(self.__class__.__name__)

class CJFilter_Model(CJFilter):
    """ Search for records of some Model

        The `model` is a reference to some django model, like `<app>.<Model>`,
        same syntax as ForeignKey resolver.

        This one contains `fields`, a dictionary of sub-filters,
        per model field.
    """
    def __init__(self, model, **kwargs):
        self._model = model
        self._model_inst = None
        self.fields = kwargs.pop('fields', {})
        super(CJFilter_Model, self).__init__(**kwargs)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self._model)

    def real_init(self):
        """Lazy initialization of filter parameters, will look into Model

            This cannot be done during `__init__()` because it would access
            some other Django models, propably not loaded yet, while this
            application is instantiated
        """
        if not self._model_inst:
            app, name = self._model.split('.', 1)
            self._model_inst = models.get_model(app, name)
        if not self.title:
            self.title = self._model_inst._meta.verbose_name  # _plural

    def getGrammar(self):
        ret = super(CJFilter_Model, self).getGrammar()
        ret['widget'] = 'model'
        ret['fields'] = {}
        for k, field in self.fields.items():
            ret['fields'][k] = field.getGrammar()
        return ret

    def _get_field(self, fname, *fpath):
        f = self.fields[fname]
        if fpath:
            return f._get_field(*fpath)
        else:
            return f

    def getResults(self, request, domain, fields=False, group_by=False,
                    limit=False, show_detail=True, **kwargs):
        objects = self._model_inst.objects
        if getattr(objects, 'by_request', None):
            objects = objects.by_request(request)
        else:
            objects = objects.all()

        if domain:
            if isinstance(domain, list) and domain[0] == 'in':
                flt = self._calc_domain(request, domain[1])
                if flt:
                    assert isinstance(flt, models.Q), "bad result from _calc_domain(): %r" % flt
                    objects = objects.filter(flt)
            else:
                raise ValueError("Domain must be like: [in, [...]]")
        if fields:
            # convert fields to django-like exprs
            fields2 = map(lambda x: x.replace('.', '__'), fields)
        else:  # not fields
            fields2 = self.fields.keys()
            # fields.sort(key=lambda f: self.fields[f].sequence) # done at JS side

        if group_by:
            group_fields = {}
            gvalues = []
            gorder_by = []
            gb_values_cache = {}
            ret = [{ 'group_level': 0, '_count': objects.count(), "values": []},]

            # First pass: resolve the fields that need to be used for groupping
            for gb in group_by:
                field = self._get_field(*(gb.split('.')))

                if not field:
                    raise KeyError("Invalid field %s for model %s" %(gb, self._model))

                gbf = []
                for f in fields:
                    if f.startswith(gb+'.'):
                        gbf.append(f[len(gb)+1:].replace('.', '__'))
                oby = gb.replace('.', '__')
                group_fields[gb] = field, gbf, oby
                gvalues.append(oby)
                if isinstance(field, CJFilter_Model):
                    oby2 = oby + '__id'
                    gorder_by.append(oby2) # avoid natural order
                    if oby2 not in fields2:
                        fields2.append(oby2)
                else:
                    gorder_by.append(oby)

            # Second pass: get all /detailed/ results
            if True:
                obs2 = objects
                if limit:
                    obs2 = objects.order_by(*gorder_by)[:limit]

                detailed_results = obs2.values('id', *fields2)
                # all_ids = [o.id for o in detailed_results]

            # Third pass: get results for each level of groupping
            i = 0
            gb_filter = {}
            while i < len(group_by):
                gb = group_by[i]
                i += 1
                go_by = gorder_by[:i]
                gvals = gvalues[:i]
                field, gbf, oby = group_fields[gb]

                # get possible values from limited objects:
                gb_vals = list(set([o[0] for o in obs2.values_list(oby)]))
                if limit:
                    gb_filter[oby+'__in'] = gb_vals

                # now, get some results:
                grp_results = objects.filter(**gb_filter).order_by(*go_by).values(*gvals).annotate(count=models.Count('pk'))

                vals_group = {}
                if isinstance(field, CJFilter_Model):
                    for g in field._model_inst.objects.filter(pk__in=gb_vals).values('id', *gbf):
                        g2 = {}
                        for k, v in g.items():
                            g2[gb + '.' + k.replace('__', '.')] = v
                        vals_group[g['id']] = g2

                gb_values_cache[gb] = vals_group

                vals = []
                for gr in grp_results:
                    row = {}
                    for k, v in gr.items():
                        if k == 'count':
                            row['_count'] = v
                        else:
                            k = k.replace('__', '.')
                            row.update(gb_values_cache[k].get(v, {k: v}))
                    vals.append(row)

                ret.append({'group_level': i,
                            'group_by': map(lambda x: x.replace('__', '.'), go_by),
                            'values': vals })

            # last, the detailed results
            if show_detail:
                ret.append({'group_level': len(gvalues)+1,
                        'values': map(_expand_keys, detailed_results)})

            return ret

            # We query on the foreign field now, and paginate that to limit the results
            # grp_queryset = rel_field.rel.to.objects.filter(id__in=grp_rdict1.keys())
        else:
            if limit:
                objects = objects[:limit]
            return objects.values('id', *fields2)

    def getQuery(self, request, name, domain):
        """query filter against /our/ model

            @params domain a 3-item list/tuple, domain expression segment
        """
        if domain[1] == '=':
            if (domain[2] is True) or (domain[2] is False):
                return { name + '__isnull': not domain[2]}
            elif not isinstance(domain[2], (int, long)):
                raise TypeError("RHS must be integer, not %r" % domain[2])
            return { name+'__pk': domain[2] }
        elif domain[1] == 'in' and all([isinstance(x, (long, int)) for x in domain[2]]):
            return { name+'__pk__in': domain[2] }
        elif domain[1] == 'in':
            objects = self._model_inst.objects
            if getattr(objects, 'by_request', None):
                objects = objects.by_request(request)
            else:
                objects = objects.all()
            flt = self._calc_domain(request, domain[2])
            if flt:
                assert isinstance(flt, models.Q), "bad result from _calc_domain(): %r" % flt
                objects = objects.filter(flt)
            return { name + '__in': objects }
        else:
            raise ValueError("Invalid operator for model: %r" % domain[1])

    def _calc_domain(self, request, domain):
        """ Parse a _list_ of domain expressions into a Query filter
        """
        ret = []
        op_stack = []
        for d in domain:
            if d in ('!', '|', '&'):
                op_stack.append(d)
                continue
            if isinstance(d, (tuple, list)) and len(d) == 3:
                field = self.fields[d[0]] # KeyError means we're asking for wrong field!
                ff = field.getQuery(request, d[0], d)
                if isinstance(ff, models.Q):
                    pass
                elif isinstance(ff, dict):
                    ff = models.Q(**ff)
                else:
                    raise TypeError("Bad query: %r" % ff)

                ret.append(ff)
            else:
                raise ValueError("Invalid domain expression: %r" % d)

            while len(op_stack) and len(ret):
                if op_stack[-1] == '!':
                    r = ret.pop()
                    ret.append(~r)
                    op_stack.pop()
                    continue
                if len(ret) < 2:
                    break
                op = op_stack.pop()
                b = ret.pop()
                a = ret.pop()
                if op == '&':
                    ret.append(a & b)
                elif op == '|':
                    ret.append(a | b)
                else:
                    raise RuntimeError("Invalid operator %r in op_stack" % op_stack[-1])
        if len(op_stack):
            raise RuntimeError("Remaining operators: %r in op_stack" % op_stack)
        if not ret:
            return models.Q()
        while len(ret) > 1:
            b = ret.pop()
            a = ret.pop()
            ret.append(a & b)

        return ret[0]

class CJFilter_Product(CJFilter_Model):

    def getGrammar(self):
        ret = super(CJFilter_Product, self).getGrammar()
        ret['widget'] = 'model-product'
        return ret

class CJFilter_isset(CJFilter):
    title = _('Non-zero')
    sequence = 2

    def getGrammar(self):
        ret = super(CJFilter_isset, self).getGrammar()
        ret['widget'] = 'isset'
        return ret

    def getQuery(self, request, name, domain):
        return {}

class CJFilter_String(CJFilter):
    sequence = 9

    def getGrammar(self):
        ret = super(CJFilter_String, self).getGrammar()
        ret['widget'] = 'char'
        return ret

    def getQuery(self, request, name, domain):
        if isinstance(domain, (list, tuple)) and len(domain) == 3:
            if domain[1] == '=':
                return { domain[0]: domain[2] }
            elif domain[1] in ('contains', 'icontains'):
                return {domain[0]+'__' + domain[1]: domain[2]}
        raise TypeError("Bad domain: %r", domain)

class CJFilter_lookup(CJFilter_Model):
    """Select *one* of some related model, with an autocomplete field
    """

    def __init__(self, model, lookup, **kwargs):
        self.lookup = lookup
        self.fields = {}
        super(CJFilter_lookup, self).__init__(model, **kwargs)

    def getGrammar(self):
        ret = super(CJFilter_lookup, self).getGrammar()
        # del ret['fields']
        ret['widget'] = 'lookup'
        ret['lookup'] = reverse('ajax_lookup', args=[self.lookup,])
        return ret

class CJFilter_Choices(CJFilter_Model):
    """ Like lookup, but offer all the choices in the grammar
    """
    filter_expr = None

    def getGrammar(self):
        ret = super(CJFilter_Choices, self).getGrammar()
        ret['widget'] = 'selection'
        objects = self._model_inst.objects
        if True:
            objects = objects.all()
        if self.filter_expr:
            objects = objects.filter(**self.filter_expr)
        ret['selection'] = [(o.id, unicode(o)) for o in objects]
        return ret

class CJFilter_contains(CJFilter):
    """ Filter for an array that must contain *all of* the specified criteria

        "sub" is the filter for each of the criteria, but will be repeated N times
        and request to satisfy all of those N contents.
    """
    def __init__(self, sub_filter, **kwargs):
        assert isinstance(sub_filter, CJFilter), repr(sub_filter)
        self.sub = sub_filter
        self.name_suffix = None
        super(CJFilter_contains, self).__init__(**kwargs)

    def __repr__(self):
        return "<%s (%s)>" % (self.__class__.__name__, repr(self.sub))

    def getGrammar(self):
        ret = super(CJFilter_contains, self).getGrammar()
        ret['widget'] = 'contains'
        ret['sub'] = self.sub.getGrammar()
        return ret

    def getQuery(self, request, name, domain):
        """query filter against a single entry
        """
        if domain[1] == '=':
            if (domain[2] is True) or (domain[2] is False):
                return { name + '__isnull': not domain[2]}
            elif not isinstance(domain[2], (list, tuple)):
                raise TypeError("RHS must be list, not %r" % domain[2])
            name2 = name
            if self.name_suffix:
                name2 += '__' + self.name_suffix
            return self.sub.getQuery(request, name2, [domain[0], 'in', [domain[2]]])
        else:
            raise ValueError("Invalid operator for contains: %r" % domain[1])

class CJFilter_attribs(CJFilter_Model):
    name_suffix = 'value'
    #def __init__(self, sub_filter, **kwargs):
    #    assert isinstance(sub_filter, CJFilter), repr(sub_filter)
    #    self.sub = sub_filter
    #    super(CJFilter_contains, self).__init__(**kwargs)

    def getGrammar(self):
        ret = super(CJFilter_attribs, self).getGrammar()
        ret['widget'] = 'attribs'
        # ret['sub'] = self.sub.getGrammar()
        return ret

    def getQuery(self, request, name, domain):
        name2 = name + '__' + self.name_suffix
        return super(CJFilter_attribs, self).getQuery(request, name2, domain)

class CJFilter_attribs_multi(CJFilter_attribs):
    def getGrammar(self):
        ret = super(CJFilter_attribs_multi, self).getGrammar()
        ret['widget'] = 'attribs_multi'
        return ret

department_filter = CJFilter_Model('company.Department', sequence=5,
    fields={ '_': CJFilter_isset(sequence=0),
            'name':  CJFilter_String(title=_('name'), sequence=1),
            'code': CJFilter_String(title=_('code'), sequence=2),
            'dept_type': CJFilter_lookup('company.DepartmentType', 'department_type',
                        fields={'name':  CJFilter_String(title=_('name'), sequence=1), }
                ),
            'nom_name':  CJFilter_String(title=_('Nom Name'), sequence=15),
            'ota_name':  CJFilter_String(title=_('OTA Name'), sequence=16),
            'parent': CJFilter_lookup('company.Department', 'department',
                title=_("parent department"),
                fields={'name':  CJFilter_String(title=_('name'), sequence=1),}),
            },
    famfam_icon='building',
    )
location_filter = CJFilter_Model('common.Location',
    fields={'name':  CJFilter_String(title=_('name'), sequence=1),
            'department': department_filter,
            'template': CJFilter_Choices('common.LocationTemplate',
                    fields={'name': CJFilter_String(title=_('name'), sequence=1), }),
        },
    famfam_icon='map', condition=user_is_staff,
    )
manuf_filter = CJFilter_lookup('products.Manufacturer', 'manufacturer',
    fields={'name':  CJFilter_String(title=_('name'), sequence=1),
        },
    famfam_icon='status_online',
    )

product_filter = CJFilter_Product('products.ItemTemplate',
    sequence=20,
    fields = {
            'description': CJFilter_String(title=_('name'), sequence=1),
            'category': CJFilter_lookup('products.ItemCategory', 'categories', sequence=5,
                    fields={'name':  CJFilter_String(title=_('name'), sequence=1),} ),
            'manufacturer': manuf_filter,
            'attributes': CJFilter_attribs_multi('products.ItemTemplateAttributes', sequence=15),
            },
    famfam_icon='camera',
    )

item_templ_c_filter = CJFilter_Model('assets.Item', title=_('asset'),
    fields = {
        'item_template': product_filter,
        },
    famfam_icon = 'computer',
    )

item_templ_filter = CJFilter_Model('assets.Item', title=_('asset'),
    fields = {
            'location': location_filter,
            'item_template': product_filter,
            'itemgroup': CJFilter_contains(item_templ_c_filter,
                            title=_('containing'), name_suffix='items',
                            sequence=25),
            },
    famfam_icon = 'computer',
    )

# ---------------- Cache ---------------

_reports_cache = {}

def _reports_init_cache():
    """ Global function, fill `_reports_cache` with pre-rendered data
    """
    if _reports_cache:
        return

    for rt in CJFilter._instances:
        rt.real_init()

    # These types will be used as top-level reports:
    _reports_cache['main_types'] = {
            'items': item_templ_filter,
            'products': product_filter,
            'department': department_filter,
            'location': location_filter,
            }

    _reports_cache['available_types'] = [ rt.to_main_report(k) for k, rt in _reports_cache['main_types'].items()]

def get_allowed_rtypes(context):
    """Return list of allowed report types

        @param context like in (obj,context) parameters of menu conditions
    """
    _reports_init_cache()
    ret = []
    for k, rt in _reports_cache['main_types'].items():
        if getattr(rt, 'condition', None):
            if rt.condition(None, context):
                pass
            else:
                continue
        ret.append(k)
    return ret

def get_rtype_name(rep_type):
    """ Get the human-readable name for some report type
    """
    _reports_init_cache()
    rt = _reports_cache['main_types'].get(rep_type, False)
    if not rt:
        raise KeyError("No report type: %s" % rep_type)
    return rt.title

# ------------------ Views -------------

def reports_app_view(request, object_id=None):
    if not request.user.is_authenticated:
        raise PermissionDenied
    _reports_init_cache()
    context = {'request': request, 'user': request.user}
    allowed_types = get_allowed_rtypes(context)
    avail = filter(lambda r: r['id'] in allowed_types, _reports_cache['available_types'])
    return render(request, 'reports_app.html',
            {'available_types': SafeString(json.dumps(avail, cls=JsonEncoderS)),
            })

def reports_parts_params_view(request, part_id):
    if not request.user.is_authenticated:
        raise PermissionDenied
    _reports_init_cache()
    if part_id not in _reports_cache['main_types']:
        return HttpResponseNotFound("Part for type %s not found" % part_id)

    return render(request, 'params-%s.html' % part_id, {})

def reports_grammar_view(request, rep_type):
    if not request.user.is_authenticated:
        raise PermissionDenied
    _reports_init_cache()

    rt = _reports_cache['main_types'].get(rep_type, False)
    if not rt:
        return HttpResponseNotFound("Grammar for type %s not found" % rep_type)
    content = json.dumps(rt.getGrammar(), cls=JsonEncoderS)
    return HttpResponse(content, content_type='application/json')

def reports_cat_grammar_view(request, cat_id):
    """Return the category-specific grammar (is_bundle and attributes)
    """
    from products.models import ItemCategory
    if not request.user.is_authenticated:
        raise PermissionDenied
    category = get_object_or_404(ItemCategory, pk=cat_id)
    ret = {'is_bundle': category.is_bundle, 'is_group': category.is_group,
            }
    if category.is_bundle or category.is_group:
        cmc = []
        for mc in category.may_contain.all():
            cmc.append((mc.category.id, mc.category.name))
        if cmc:
            ret['may_contain'] = cmc

    ret['attributes'] = []
    for attr in category.attributes.all():
        ret['attributes'].append({'aid': attr.id, 'name': attr.name,
                'values': attr.values.values_list('id', 'value')})

    return HttpResponse(json.dumps(ret, cls=JsonEncoderS),
                        content_type='application/json')

def _expand_keys(dd):
    """ expand dictionary keys from Django double-underscore to dot
    """
    ret = {}
    for k, v in dd.items():
        ret[k.replace('__', '.')] = v
    return ret

def reports_get_preview(request, rep_type):
    """Return a subset of results, for some report
    """
    if not request.user.is_authenticated:
        raise PermissionDenied
    _reports_init_cache()

    rt = _reports_cache['main_types'].get(rep_type, False)
    if not rt:
        return HttpResponseNotFound("Report type %s not found" % rep_type)

    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST',])

    req_data = json.loads(request.body)
    assert (req_data['model'] == rep_type), "invalid model: %r" % req_data['model']

    req_data.setdefault('limit', 10)
    res = rt.getResults(request, **req_data)

    if isinstance(res, QuerySet):
        res = {'results': map(_expand_keys, res),
                'count': res.count(),
                }
    elif isinstance(res, list):
        pass
    else:
        raise TypeError("Bad result type: %s" % type(res))
    content = json.dumps(res, cls=JsonEncoderS)
    return HttpResponse(content, content_type='application/json')

def reports_back_list_view(request):
    if not request.user.is_authenticated:
        raise PermissionDenied
    res = SavedReport.objects.by_request(request).distinct().values('id', 'title', 'rmodel')
    content = json.dumps(res, cls=JsonEncoderS)
    return HttpResponse(content, content_type='application/json')

def reports_back_load_view(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET',])
    if not request.user.is_authenticated:
        raise PermissionDenied

    _reports_init_cache()
    if not request.GET.get('id', False):
        raise HttpResponseNotFound("No ID in GET")
    report = get_object_or_404(SavedReport.objects.by_request(request), pk=request.GET['id'])

    rt = _reports_cache['main_types'].get(report.rmodel, False)
    if not rt:
        return HttpResponseNotFound("Grammar for type %s not found" % report.rmodel)

    ret = {'id': report.id, 'title': report.title, 'model': report.rmodel,
            'public': not bool(report.owner),
            'grammar': rt.getGrammar(), 'data': json.loads(report.params)}
    content = json.dumps(ret, cls=JsonEncoderS)
    return HttpResponse(content, content_type='application/json')


def reports_back_save_view(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST',])
    if not request.user.is_authenticated:
        raise PermissionDenied

    req_data = json.loads(request.body)

    # Staff can create public reports, all other users only private ones
    if request.user.is_staff and req_data['public']:
        req_data['owner'] = None
    elif not req_data['public']:
        req_data['owner'] = request.user
    else:
        raise PermissionDenied()

    report = None
    if req_data.get('id', None):
        report = get_object_or_404(SavedReport.objects.by_request(request), pk=req_data['id'])
    else:
        report = SavedReport()

    report.title = req_data['title']
    report.owner = req_data['owner']
    report.rmodel = req_data['model']
    report.params = json.dumps(req_data['data'])
    report.save()
    return HttpResponse(json.dumps({'id': report.id }), content_type='application/json')

def reports_back_del_view(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST',])
    if not request.user.is_authenticated:
        raise PermissionDenied

    req_data = json.loads(request.body)
    if not req_data.get('confirm', None):
        raise PermissionDenied()

    report = get_object_or_404(SavedReport.objects.by_request(request), pk=req_data['id'])

    # Staff can delete public reports, all other users only private ones
    if (request.user.is_staff or request.user.is_superuser) and not report.owner:
        pass
    elif request.user == report.owner:
        pass
    else:
        raise PermissionDenied()

    report.delete()
    return HttpResponse(_("Report deleted"), content_type='text/plain')

def _pre_render_report(request):
    """Decode request parameters and prepare a report to be rendered
    """
    if not request.user.is_authenticated:
        raise PermissionDenied
    
    _reports_init_cache()
    if request.method == 'POST':
        report_data = json.loads(request.POST['data'])
    #elif request.method == 'GET':
        # Won't work, we need the algorithm of the JS part for domains, fields
        #report = get_object_or_404(SavedReport.objects.by_request(request), \
                        #pk=request.GET['id'])

        #report_data = {'id': report.id, 'title': report.title, 'model': report.rmodel,
            #'public': not bool(report.owner),
            #'data': json.loads(report.params)}
    else:
        return HttpResponseNotAllowed(['POST']) # +GET ?
    
    report_model = report_data.pop('model')
    rt = _reports_cache['main_types'].get(report_model, False)
    if not rt:
        return HttpResponseNotFound("Report type %s not found" % report_model)

    fin = {'report_data': report_data,
            'field_cols': report_data.pop('field_cols'),
            'groupped_fields': report_data.pop('groupped_fields'),
        }

    res = rt.getResults(request, **(report_data))
    if isinstance(res, QuerySet):
        fin['flat_results'] = res
    elif isinstance(res, list):
        fin['groupped_results'] = res

    return fin

def reports_results_html(request):
    """Retrieve results, rendered in a html page
    """
    return render(request, 'reports_results.html', _pre_render_report(request))

def reports_results_pdf(request):
    raise NotImplementedError

def reports_results_csv(request):
    raise NotImplementedError

# eof