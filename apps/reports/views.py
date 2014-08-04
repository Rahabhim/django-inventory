# -*- encoding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseNotFound, HttpResponse, HttpResponseNotAllowed
from django.core.urlresolvers import reverse
from django.utils.functional import Promise
from django.db import models
from django.db.models.query import QuerySet
from django.contrib import messages
import json
import datetime
from django.utils.safestring import SafeString
from collections import defaultdict
from django.core.exceptions import ObjectDoesNotExist
import csv

from models import SavedReport
from common.api import user_is_staff
import logging

# ------ Utility classes ------

class JsonEncoderS(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return unicode(obj)
        elif isinstance(obj, QuerySet):
            return list(obj)
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        return super(JsonEncoderS, self).default(obj)

class QryPlaceholder(object):
    """ Placeholder for Django Query values

        A placeholder will behave like a string, but also be preserved
        along the query build-up, so that we can substitute it *late*.

        We do that because the inner query has to reference the 'id'
        field of the outer query, for which Django has no provision.
        Django, however, will respect our `._prepare()` method and
        thus avoid converting this value.
    """
    _index = 0

    def __init__(self, ss=''):
        self.s = ss

    def _prepare(self):
        if not self.s:
            self.s = '<placeholder_%x>' % self._index
            QryPlaceholder._index += 1
        return self

    def __str__(self):
        return self.s

    def set(self, s):
        self.s = s

    @staticmethod
    def trans_params(e, query):
        """ Replace placeholders with outer query "id" column reference

            @param e a dict of Query.extra() parameters (having 'where' and 'params')
            @param query the outer Query instance

            @returns None, it updates "e" in-place
        """
        if not ('where' in e and 'params' in e):
            return
        assert len(e['where']) == 1, repr(e['where'])
        lp = []
        params2 = []
        found = False
        for p in e['params']:
            if isinstance(p, QryPlaceholder):
                lp.append(query.get_initial_alias() + '.id')
                found = True
            else:
                lp.append('%s')
                params2.append(p)
        if found:
            e['where'][0] = e['where'][0] % tuple(lp)
            e['params'] = params2

class ExtraQuery(object):
    """ Query clause, resolving to `.extra()` attributes

        This object will hold a subquery plus its outer clause. We dive
        deep into the mechanics of Django.models.query.Query, exploit it
        in order to construct a proper sub-query for our models.
    """
    def __init__(self, qset, related_name=False):
        if isinstance(qset, ExtraQuery):
            self._placeholder_mark = qset._placeholder_mark
            self.query = qset.query.clone()
            self.clause = qset.clause
            self.name = qset.name
        else:
            self._placeholder_mark = QryPlaceholder()
            self.clause = None
            self.name = '_extra'
            try:
                self.query = qset
                self.query.default_cols = False
                self.query.clear_select_fields()
                self.query.clear_ordering(True)
                self.query.clear_limits()
                self.query.select_for_update = False
                self.query.select_related = False
                self.query.related_select_cols = []
                self.query.related_select_fields = []
                self.query.add_filter((related_name, self._placeholder_mark))
            except Exception:
                logging.getLogger('apps').exception("related_name")
                raise
            self.query.bump_prefix()

    def __repr__(self):
        return '<Extra: %s %s %r>' % (self.name or '', self.query, self.clause or '')

    def clone(self):
        return ExtraQuery(self)

    def setQueryExtras(self, extras, qdic):
        """ Populate extras with dict for `QuerySet.extra()`, qdic with clauses
        """
        query, params = self.query.sql_with_params()
        if self.clause:
            ex = {}
            ex['where'] = [ '(%s) %s %%s' % (query, self.clause[0])]
            ex['params'] = list(params) + [ self.clause[1]]
            extras.append(ex)


# ----------- Filters ----------------

class CJFilter(object):
    """Base for some search criterion, represents a search field
    """
    title = ''
    _instances = []
    sequence = 10
    _post_fn = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        CJFilter._instances.append(self)

    def __repr__(self):
        return "<%s >" % self.__class__.__name__

    def copy(self, **kwargs):
        """Copy of the Filter instance, with some attributes modified
        """
        kkw = {}
        for k, v in self.__dict__.items():
            if k.startswith('_'):
                continue
            kkw[k] = v
        kkw.update(**kwargs)
        return self.__class__(**kkw)

    def real_init(self):
        pass

    def getGrammar(self, is_staff=False):
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
        self.model = model
        self._model_inst = None
        self.fields = kwargs.pop('fields', {})
        super(CJFilter_Model, self).__init__(**kwargs)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.model)

    def real_init(self):
        """Lazy initialization of filter parameters, will look into Model

            This cannot be done during `__init__()` because it would access
            some other Django models, propably not loaded yet, while this
            application is instantiated
        """
        if not self._model_inst:
            app, name = self.model.split('.', 1)
            self._model_inst = models.get_model(app, name)
        if not self.title:
            self.title = self._model_inst._meta.verbose_name  # _plural

    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_Model, self).getGrammar(is_staff)
        ret['widget'] = 'model'
        ret['fields'] = {}
        for k, field in self.fields.items():
            if getattr(field, 'staff_only', False) and not is_staff:
                continue
            ret['fields'][k] = field.getGrammar(is_staff)
        return ret

    def _get_field(self, fname, *fpath):
        f = self.fields.get(fname, None)
        if f is None:
            return None
        if fpath:
            return f._get_field(*fpath)
        else:
            return f

    def getResults(self, request, domain, fields=False, group_by=False,
                    limit=False, show_detail=True, order_by=False, **kwargs):
        objects = self._model_inst.objects
        if getattr(objects, 'by_request', None):
            objects = objects.by_request(request)
        else:
            objects = objects.all()

        order_by2 = []
        if order_by:
            for o in order_by:
                # the data field, then the expression
                if o.startswith(('+', '-')):
                    order_by2.append((o[1:]+'.', o))
                else:
                    order_by2.append((o+'.', o))
        if domain:
            if isinstance(domain, list) and domain[0] == 'in':
                extras = []
                flt = self._calc_domain(request, domain[1], extras)
                for e in extras:
                    QryPlaceholder.trans_params(e, objects.query)
                    objects = objects.extra(**e)
                if flt:
                    assert isinstance(flt, models.Q), "bad result from _calc_domain(): %r" % flt
                    objects = objects.filter(flt)
            else:
                raise ValueError("Domain must be like: [in, [...]]")

        post_fns = {}
        if fields:
            # convert fields to django-like exprs
            fields2 = []
            for fn in fields:
                fpath = fn.split('.')
                fld = self._get_field(*fpath)
                if fld is None:
                    continue
                if not (fn.startswith('_') or isinstance(fld, (CJFilter_contains, CJFilter_attribs))):
                    fields2.append(fn.replace('.', '__'))
                if fld._post_fn:
                    post_fns[fn.replace('.', '__')] = fld._post_fn
        else:  # not fields
            fields2 = filter(lambda f: not (f.startswith('_') or isinstance(fld, (CJFilter_contains, CJFilter_attribs))), self.fields.keys())
            # fields.sort(key=lambda f: self.fields[f].sequence) # done at JS side
            for fn, fld in self.fields.items():
                if fld._post_fn:
                    post_fns[fn] = fld._post_fn

        if group_by:
            group_fields = {}
            gvalues = []
            gorder_by = []
            go_backmap = {} # map of "gorder_by" entries not same as group_by
            gb_values_cache = {}
            ret = [{ 'group_level': 0, '_count': objects.count(), "values": []},]

            # First pass: resolve the fields that need to be used for groupping
            for gb in group_by:
                field = self._get_field(*(gb.split('.')))

                if not field:
                    raise KeyError("Invalid field %s for model %s" %(gb, self.model))

                gbf = []
                for f in fields:
                    if f.startswith(gb+'.'):
                        gbf.append(f[len(gb)+1:].replace('.', '__'))

                oby = gb.replace('.', '__')
                while order_by2 and order_by2[0][0].startswith(gb+'.'):
                    gorder_by.append(order_by2[0][1].replace('.', '__'))
                    del order_by2[0]

                if isinstance(field, CJFilter_Model):
                    oby2 = oby + '__id'
                    if not field._model_inst._meta.parents:
                        # Django db backend borks if we try to order by inheriting id
                        gorder_by.append(oby2) # avoid natural order
                    else:
                        gorder_by.append(oby)
                        go_backmap[oby] = oby2

                    if oby2 not in fields2:
                        fields2.append(oby2)
                else:
                    gorder_by.append(oby)
                group_fields[gb] = field, gbf, oby, list(gorder_by)
                gvalues.append(oby)

            for go in order_by2:
                gorder_by.append(go[1].replace('.', '__'))

            # Second pass: get all /detailed/ results
            if True:
                obs2 = objects
                if limit:
                    obs2 = objects.order_by(*gorder_by)[:limit]

                detailed_results = obs2.values('id', *fields2)
                # all_ids = [o.id for o in detailed_results]
                for fn, _post_fn in post_fns.items():
                    _post_fn(fn, detailed_results, obs2)

            # Third pass: get results for each level of groupping
            i = 0
            gb_filter = {}
            while i < len(group_by):
                gb = group_by[i]
                i += 1
                gvals = gvalues[:i]
                field, gbf, oby, go_by = group_fields[gb]

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
                            'group_by': map(lambda x: go_backmap.get(x,x).replace('__', '.'), go_by),
                            'values': vals })

            # last, the detailed results
            if show_detail:
                ret.append({'group_level': len(gvalues)+1,
                        'values': map(_expand_keys, detailed_results)})

            return ret

            # We query on the foreign field now, and paginate that to limit the results
            # grp_queryset = rel_field.rel.to.objects.filter(id__in=grp_rdict1.keys())
        else:
            count = objects.count()
            if order_by:
                objects = objects.order_by(*[o.replace('.', '__') for o in order_by])
            if limit:
                objects = objects[:limit]
            detailed_results = objects.values('id', *fields2)
            for fn, _post_fn in post_fns.items():
                _post_fn(fn, detailed_results, objects)
            return detailed_results, count

    def getQuery(self, request, name, domain):
        """query filter against /our/ model

            @params domain a 3-item list/tuple, domain expression segment
        """
        if domain[1] == '=':
            if (domain[2] is True) or (domain[2] is False):
                return { name + '__isnull': not domain[2]}
            elif isinstance(domain[2], basestring) and domain[2].isdigit():
                return { name+'__pk': int(domain[2]) }
            elif not isinstance(domain[2], (int, long)):
                raise TypeError("RHS must be integer, not %r" % domain[2])
            return { name+'__pk': domain[2] }
        elif domain[1] == 'in' and all([isinstance(x, (long, int)) for x in domain[2]]):
            return { name+'__pk__in': domain[2] }
        elif domain[1] == 'in':
            objects = self._model_inst.objects
            extras = []
            if getattr(objects, 'by_request', None):
                objects = objects.by_request(request)
            else:
                objects = objects.all()
            flt = self._calc_domain(request, domain[2], extras)
            for e in extras:
                QryPlaceholder.trans_params(e, objects.query)
                objects = objects.extra(**e)
            if flt:
                assert isinstance(flt, models.Q), "bad result from _calc_domain(): %r" % flt
                objects = objects.filter(flt)
            return { name + '__in': objects }
        else:
            raise ValueError("Invalid operator for model: %r" % domain[1])

    def _calc_domain(self, request, domain, extras):
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
                elif isinstance(ff, list) and all([isinstance(x,ExtraQuery) for x in ff]):
                    td = {} # will receive WHERE clauses
                    for f in ff:
                        f.setQueryExtras(extras, td)
                    if td:
                        ff = models.Q(**td)
                    else:
                        ff = None
                else:
                    raise TypeError("Bad query: %r" % ff)

                if ff is not None:
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

    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_Product, self).getGrammar(is_staff)
        ret['widget'] = 'model-product'
        return ret

class CJFilter_isset(CJFilter):
    title = _('Non-zero')
    sequence = 2

    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_isset, self).getGrammar(is_staff)
        ret['widget'] = 'isset'
        return ret

    def getQuery(self, request, name, domain):
        return {}

class CJFilter_String(CJFilter):
    sequence = 9

    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_String, self).getGrammar(is_staff)
        ret['widget'] = 'char'
        return ret

    def getQuery(self, request, name, domain):
        if isinstance(domain, (list, tuple)) and len(domain) == 3:
            if domain[1] == '=':
                return { domain[0]: domain[2] }
            elif domain[1] in ('contains', 'icontains'):
                return {domain[0]+'__' + domain[1]: domain[2]}
        raise TypeError("Bad domain: %r", domain)

def to_date(d):
    if isinstance(d, basestring):
        return datetime.datetime.strptime(d, '%Y-%m-%d').date()
    elif isinstance(d, (datetime.date)):
        return d
    else:
        raise TypeError("Date from %s" % type(d))

class CJFilter_date(CJFilter):
    _query_ops = { '=': '', '>': '__gt', '<': '__lt',
            '>=': '__gte', '<=': '__lte',
            }

    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_date, self).getGrammar(is_staff)
        ret['widget'] = 'date'
        return ret

    def getQuery(self, request, name, domain):
        if isinstance(domain, (list, tuple)) and len(domain) == 3:
            if domain[1] == 'between':
                ret = {}
                if domain[2][0]:
                    ret[domain[0] +'__gte'] = to_date(domain[2][0])
                if domain[2][1]:
                    ret[domain[0] + '__lte'] = to_date(domain[2][1])
                return ret
            elif domain[1] in self._query_ops:
                lhs = domain[0] + self._query_ops[domain[1]]
                return { lhs: to_date(domain[2]) }

        raise TypeError("Bad domain: %r", domain)

class CJFilter_Boolean(CJFilter):

    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_Boolean, self).getGrammar(is_staff)
        ret['widget'] = 'boolean'
        return ret

    def getQuery(self, request, name, domain):
        if isinstance(domain, (list, tuple)) and len(domain) == 3:
            if domain[1] == '=':
                return { domain[0]: domain[2] }
        raise TypeError("Bad domain: %r", domain)

class CJFilter_id(CJFilter):
    title = _('ID')
    sequence = 1

    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_id, self).getGrammar(is_staff)
        ret['widget'] = 'id'
        return ret

    def getQuery(self, request, name, domain):
        return {}

    def _post_fn(self, fname, results, qset):
        urls = {}
        for o in qset:
            urls[o.id] = o.get_absolute_url()

        for row in results:
            row[fname +'.url'] = urls.get(row['id'],False)

class CJFilter_dept_has_assets(CJFilter_Boolean):
    """Special filter that finds only Departments with/without assets
    """
    staff_only = True    # by default, this field is too expensive to compute

    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_dept_has_assets, self).getGrammar(is_staff)
        ret['widget'] = 'has_sth'
        return ret

    def getQuery(self, request, name, domain):
        from company.models import Department
        if isinstance(domain, (list, tuple)) and len(domain) == 3 \
                and (domain[1] == '='):
            q = models.Q(location__item__isnull=False)
            if domain[2]:
                # pass through Q, to get unique results
                return models.Q(id__in=Department.objects.filter(q))
            else:
                # we cannot just say "location__item__isnull=True", because
                # it would take Departments having /one/ of their locations
                # empty. So, we invert the result set of those having any
                # assets.
                return ~models.Q(id__in=Department.objects.filter(q))
        raise TypeError("Bad domain: %r", domain)

    def _post_fn(self, fname, results, qset):
        from company.models import Department
        # use Department.objects again, because qset is already sliced
        all_ids = qset.values_list('id', flat=True)
        # Django is smart enough to keep `all_ids` decorated with the
        # original query, so that filter(id__in=all_ids) will be
        # implemented using a nested sub-query.
        #
        # But MySQL isn't.
        # http://dev.mysql.com/doc/refman/5.5/en/subquery-restrictions.html
        # A nested sub-query, in MySQL, cannot have LIMIT. So, we need
        # to force Django to use a plain list of IDs
        depts_with = set(Department.objects.filter(id__in=list(all_ids)). \
                    filter(location__item__isnull=False).distinct()\
                    .values_list('id', flat=True))

        for row in results:
            row[fname] = bool(row['id'] in depts_with)

class CJFilter_lookup(CJFilter_Model):
    """Select *one* of some related model, with an autocomplete field
    """

    def __init__(self, model, lookup, **kwargs):
        self.lookup = lookup
        self.fields = {}
        super(CJFilter_lookup, self).__init__(model, **kwargs)

    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_lookup, self).getGrammar(is_staff)
        # del ret['fields']
        ret['widget'] = 'lookup'
        ret['lookup'] = reverse('ajax_lookup', args=[self.lookup,])
        return ret

class CJFilter_ModelChoices(CJFilter_Model):
    """ Like lookup, but offer all the choices in the grammar
    """
    filter_expr = None

    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_ModelChoices, self).getGrammar(is_staff)
        ret['widget'] = 'selection'
        objects = self._model_inst.objects
        if True:
            objects = objects.all()
        if self.filter_expr:
            objects = objects.filter(**self.filter_expr)
        ret['selection'] = [(o.id, unicode(o)) for o in objects]
        return ret

class CJFilter_choices(CJFilter):
    """ Plain choices, taken from a model field
    """
    def __init__(self, model, field, **kwargs):
        self.model = model
        self.field = field
        self._field_inst = None
        super(CJFilter_choices, self).__init__(**kwargs)

    def real_init(self):
        """Lazy initialization of field, will look into Model
        """
        if not self._field_inst:
            app, name = self.model.split('.', 1)
            model_inst = models.get_model(app, name)
            self._field_inst = model_inst._meta.get_field(self.field)
        if not self.title:
            self.title = self._field_inst.verbose_name

    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_choices, self).getGrammar(is_staff)
        ret['widget'] = 'selection'
        ret['selection'] = [(k, unicode(s)) for k,s in self._field_inst.choices]
        return ret

    def getQuery(self, request, name, domain):
        if isinstance(domain, (list, tuple)) and len(domain) == 3:
            if domain[1] == '=':
                return { domain[0]: domain[2] }
            elif domain[1] == 'in':
                return { domain[0] + '__in': domain[2] }
        raise TypeError("Bad domain: %r", domain)

    def _post_fn(self, fname, results, qset):
        choices = {}
        for k,s in self._field_inst.choices:
            choices[k] = unicode(s)
        for row in results:
            row[fname] = choices.get(row[fname], row[fname])


class CJFilter_contains(CJFilter):
    """ Filter for an array that must contain *all of* the specified criteria

        "sub" is the filter for each of the criteria, but will be repeated N times
        and request to satisfy all of those N contents.
    """
    def __init__(self, sub_filter, **kwargs):
        assert isinstance(sub_filter, CJFilter), repr(sub_filter)
        self.sub_filter = sub_filter
        self.name_suffix = None
        super(CJFilter_contains, self).__init__(**kwargs)

    def __repr__(self):
        return "<%s (%s)>" % (self.__class__.__name__, repr(self.sub_filter))

    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_contains, self).getGrammar(is_staff=False)
        ret['widget'] = 'contains'
        ret['sub'] = self.sub_filter.getGrammar(is_staff)
        for k, field in self.fields.items():
            if getattr(field, 'staff_only', False) and not is_staff:
                continue
            ret['sub']['fields'][k] = field.getGrammar(is_staff)
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
            return self.sub_filter.getQuery(request, name2, [domain[0], 'in', [domain[2]]])
        elif domain[1] == 'in':
            # multiple criteria, possibly a '_count'
            name2 = name
            if self.name_suffix:
                name2 += '__' + self.name_suffix
            inner_dom = []
            count_dom = []
            for dom in domain[2]:
                if isinstance(dom, str) and dom in ('!', '&', '|'):
                    raise NotImplementedError('Operators not supported in contains yet')
                if isinstance(dom, (list, tuple)) and len(dom) == 3:
                    if dom[0] in self.fields:
                        count_dom.append(dom)
                    else:
                        inner_dom.append(dom)
                else:
                    raise ValueError("invalid expression: %r", dom)
            sq = self.sub_filter.getQuery(request, name2, [domain[0], 'in', inner_dom])
            if count_dom:
                # no longer a straight "exists" sub-query that Django can handle.
                # we need to separate it and write in a special syntax.
                qset = sq.pop(name2+'__in')
                assert not sq, "bad query: %r" % sq.keys()
                base_extra_qry = ExtraQuery(qset.query, self.related_name)
                all_extras = []
                for dom in count_dom:
                    for eq in self.fields[dom[0]].setExtraQuery(dom, base_extra_qry):
                        all_extras.append(eq)
                return all_extras
            else:
                return sq
        else:
            raise ValueError("Invalid operator for contains: %r" % domain[1])

    def _post_fn(self, fname, results, qset):
        """annotate `results` with computed value for our field `fname`

            @param qset a QuerySet, whose .values() produced `results`
        """
        if getattr(self, 'alt_model', False):
            qset2 = models.get_model(self.alt_model[0], self.alt_model[1]) \
                    .objects.filter(pk__in=[v['id'] for v in results])
        else:
            qset2 = qset
        imap = {} # id=> value map
        for ig in qset2.prefetch_related(self.name_suffix or fname):
            qset3 = getattr(ig, self.name_suffix or fname)
            cnts = [] # ordered
            cnts_c = {} # counters
            for cnt in qset3.all():
                uc = unicode(cnt)
                if uc in cnts_c:
                    cnts_c[uc] = cnts_c[uc] + 1
                else:
                    cnts_c[uc] = 1
                    cnts.append(uc)
            for i, uc in enumerate(cnts):
                if cnts_c[uc] > 1:
                    cnts[i] = uc + (' x%d' % cnts_c[uc])
            imap[ig.id] = cnts
        for row in results:
            row[fname] = imap.get(row['id'], None)

class CJFilter_attribs(CJFilter_Model):
    name_suffix = 'value'
    #def __init__(self, sub_filter, **kwargs):
    #    assert isinstance(sub_filter, CJFilter), repr(sub_filter)
    #    self.sub = sub_filter
    #    super(CJFilter_contains, self).__init__(**kwargs)

    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_attribs, self).getGrammar(is_staff)
        ret['widget'] = 'attribs'
        return ret

    def getQuery(self, request, name, domain):
        name2 = name + '__' + self.name_suffix
        return super(CJFilter_attribs, self).getQuery(request, name2, domain)

    def _post_fn(self, fname, results, qset):
        imap = {}
        for prod in qset.prefetch_related('attributes'):
            if prod.attributes.exists():
                val = []
                for attr in prod.attributes.all():
                    val.append(attr.value.value)
                imap[prod.id] = ', '.join(val)
            else:
                imap[prod.id] = ''
        for row in results:
            row[fname] = imap.get(row['id'], None)

class CJFilter_attribs_multi(CJFilter_attribs):
    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_attribs_multi, self).getGrammar(is_staff)
        ret['widget'] = 'attribs_multi'
        return ret

class CJFilter_count(CJFilter):
    title = _('count')
    sequence = 100
    operators = set(['>=', '<', '='])

    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_count, self).getGrammar(is_staff)
        ret['widget'] = 'count'
        return ret

    def setExtraQuery(self, dom, extra_query):
        """ Prepare an extra-query for the /count/ of sub-query items

            `extra_query` shall already be clean (w/o select fields, ordering etc.)
            and then we convert it to a "count" one, like the `quewry.get_count()`
            does.
        """
        qq = extra_query.clone()
        qq.query.add_count_column()
        qq.name = dom[0]
        if dom[1] not in self.operators:
            # don't allow arbitrary strings from remote !
            raise ValueError("Invalid operator")
        qq.clause = (dom[1], dom[2])
        yield qq

class CJFilter_attribs_count(CJFilter_attribs):
    sequence = 120
    operators = set(['>=', '<', '='])

    def __init__(self, model, sub_path, attribs_path='attributes', cat_path='category', **kwargs):
        super(CJFilter_attribs_count, self).__init__(model, **kwargs)
        self.sub_path = sub_path
        self.attribs_path = attribs_path
        self.cat_path = cat_path

    def getGrammar(self, is_staff=False):
        ret = super(CJFilter_attribs_count, self).getGrammar(is_staff)
        ret['widget'] = 'attribs_count'
        ret['sub_path'] = self.sub_path
        ret['attribs_path'] = self.attribs_path
        ret['cat_path'] = self.cat_path
        return ret

    def setExtraQuery(self, dom, extra_query):
        """ Prepare queries for "sum of attribute" clauses

            A bit more tricky: since attributes need to be limited to a specific
            "attribute type" (like "memory" or "speed"), we need a separate sub-
            query for each attribute type. So we clone the base query multiple
            times.
        """
        clauses = []
        if dom[1] == '=':
            clauses = [dom[2]]

        elif dom[1] == 'in':
            clauses = dom[2]

        for c in clauses:
            qq = extra_query.clone()
            qq.name = dom[0]
            qq.query.add_filter(('%s__%s__value__atype__id' % \
                            (self.sub_path, self.attribs_path), c[0]))

            aggregate = models.Sum('%s__%s__value__value_num' % \
                            (self.sub_path, self.attribs_path))
            qq.query.add_aggregate(aggregate, qq.query.model, qq.name, is_summary=True)
            if c[1] not in self.operators:
                # don't allow arbitrary strings from remote !
                raise ValueError("Invalid operator")
            qq.clause = (c[1], c[2])
            yield qq
        return

######## - model definitions


department_filter = CJFilter_Model('company.Department', sequence=5,
    fields={ '_': CJFilter_isset(sequence=0),
            'id': CJFilter_id(),
            'name':  CJFilter_String(title=_('name'), sequence=1),
            'code': CJFilter_String(title=_('code'), sequence=2),
            'dept_type': CJFilter_lookup('company.DepartmentType', 'department_type',
                        fields={'name':  CJFilter_String(title=_('name'), sequence=1), }
                ),
            '_has_assets': CJFilter_dept_has_assets(title=_("has assets"), sequence=5),
            #'nom_name':  CJFilter_String(title=_('Nom Name'), sequence=15),
            #'ota_name':  CJFilter_String(title=_('OTA Name'), sequence=16),
            'parent': CJFilter_lookup('company.Department', 'department',
                title=_("parent department"),
                fields={'name':  CJFilter_String(title=_('name'), sequence=1),
                        'code': CJFilter_String(title=_('code'), sequence=2),
                        }),
            },
    famfam_icon='building',
    )
location_filter = CJFilter_Model('common.Location',
    fields={ 'id': CJFilter_id(),
            'name':  CJFilter_String(title=_('name'), sequence=1),
            'department': department_filter,
            'template': CJFilter_ModelChoices('common.LocationTemplate',
                    fields={'name': CJFilter_String(title=_('name'), sequence=1), }),
        },
    famfam_icon='map', condition=user_is_staff,
    )
manuf_filter = CJFilter_lookup('products.Manufacturer', 'manufacturer',
    fields={ 'id': CJFilter_id(), 'name':  CJFilter_String(title=_('name'), sequence=1),
        },
    famfam_icon='status_online',
    )

users_filter = CJFilter_Model('auth.User', sequence=40,
    fields= {'id': CJFilter_id(),
            'first_name': CJFilter_String(title=_('first name'), sequence=1),
            'last_name': CJFilter_String(title=_('last name'), sequence=2),
            'username': CJFilter_String(title=_('user name'), sequence=5),
            'email': CJFilter_String(title=_('email'), sequence=10),
            },
    famfam_icon='user', condition=user_is_staff,
    )

product_filter = CJFilter_Product('products.ItemTemplate',
    sequence=20,
    fields = { 'id': CJFilter_id(),
            'description': CJFilter_String(title=_('name'), sequence=1),
            'category': CJFilter_lookup('products.ItemCategory', 'categories', sequence=5,
                    fields={'name':  CJFilter_String(title=_('name'), sequence=1),} ),
            'manufacturer': manuf_filter,
            'attributes': CJFilter_attribs_multi('products.ItemTemplateAttributes', sequence=15),
            'approved': CJFilter_Boolean(title=_("approved"), staff_only=True),
            },
    famfam_icon='camera',
    )

contract_filter = CJFilter_lookup('procurements.Contract', 'contracts',
    title=_('contract'),
    fields={ 'id': CJFilter_id(),
            'name':  CJFilter_String(title=_('name'), sequence=1),
            'delegate': CJFilter_Model('procurements.Delegate',
                fields={ 'name':  CJFilter_String(title=_('name'), sequence=1),
                }
            )
        },
    famfam_icon='basket',
    )

purchaseorder_filter = CJFilter_Model('movements.PurchaseOrder', sequence=40,
    fields={ 'id': CJFilter_id(),
            'user_id': CJFilter_String(title=_("user defined id"), sequence=1),
            'create_user': users_filter.copy(title=_("created by"), staff_only=True),
            'validate_user': users_filter.copy(title=_("validated by"), staff_only=True),
            'supplier': CJFilter_lookup('common.Supplier', 'supplier_vat',
                fields={'name':  CJFilter_String(title=_('name'), sequence=1),
                        'vat_number':  CJFilter_String(title=_('VAT number'), sequence=10),
                    }
                ),
            'issue_date': CJFilter_date(title=_("issue date")),
            'state': CJFilter_choices('movements.PurchaseOrder', 'state', title=_('state')),
            'department': department_filter,
        },
    condition=user_is_staff, famfam_icon='cart_go'
    )

item_templ_c_filter = CJFilter_Model('assets.Item', title=_('asset'),
    fields = {
        'item_template': product_filter,
        },
    famfam_icon = 'computer',
    )

item_templ_filter = CJFilter_Model('assets.Item', title=_('asset'),
    fields = {'id': CJFilter_id(),
            'location': location_filter,
            'item_template': product_filter,
            'itemgroup': CJFilter_contains(item_templ_c_filter,
                            alt_model=('assets', 'ItemGroup'),
                            title=_('containing'), name_suffix='items',
                            related_name='bundled_in',
                            fields={
                                '_count': CJFilter_count(),
                                '_sum_attribs': CJFilter_attribs_count('products.ItemTemplateAttributes', 'item_template'),
                                },
                            sequence=25),
            'src_contract': contract_filter,
            },
    famfam_icon = 'computer',
    )

inventories_filter = CJFilter_Model('inventory.InventoryGroup', title=_('inventories'),
    fields={'id': CJFilter_id(),
        'name': CJFilter_String(title=_('name'), sequence=1),
        'department': department_filter,
        'date_act': CJFilter_date(title=_("date performed")),
        'date_val': CJFilter_date(title=_("date validated")),
        'state': CJFilter_choices('inventory.InventoryGroup', 'state', title=_('state')),
        'create_user': users_filter.copy(title=_("created by"), staff_only=True),
        'validate_user': users_filter.copy(title=_("validated by"), staff_only=True),
    },
    condition=user_is_staff,
    famfam_icon='package'
    )

movements_filter = CJFilter_Model('movements.Movement', title=_("movements"),
    fields={'id': CJFilter_id(),
        'name': CJFilter_String(title=_('name'), sequence=1),
        'date_act': CJFilter_date(title=_("date performed")),
        'date_val': CJFilter_date(title=_("date validated")),
        'state': CJFilter_choices('movements.Movement', 'state', title=_('state'), sequence=4),
        'stype': CJFilter_choices('movements.Movement', 'stype', title=_('type'), sequence=5),
        'create_user': users_filter.copy(title=_("created by"), staff_only=True, sequence=20),
        'validate_user': users_filter.copy(title=_("validated by"), staff_only=True, sequence=21),
        'location_src': location_filter.copy(title=_('source location'), sequence=2),
        'location_dest': location_filter.copy(title=_('destination location'), sequence=3),
        'items': CJFilter_contains(item_templ_c_filter,
                            title=_('items'),
                            sequence=25),
    },
    condition=user_is_staff,
    famfam_icon='computer_go',
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
            'purchase_order': purchaseorder_filter,
            'inventories': inventories_filter,
            'movements': movements_filter,
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

def report_details_view(request, pk=False):
    if not request.user.is_authenticated:
        raise PermissionDenied
    report = get_object_or_404(SavedReport.objects.by_request(request), pk=pk)
    return render(request, 'report_details.html', { 'report': report })

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
    content = json.dumps(rt.getGrammar(request.user.is_staff), cls=JsonEncoderS)
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
    if req_data.get('show_detail', True) and req_data['limit'] > 200:
        req_data['limit'] = 200
    elif (not req_data.get('show_detail', True)) and req_data['limit'] > 1000:
        req_data['limit'] = 1000

    res = rt.getResults(request, **req_data)

    if isinstance(res, tuple) and isinstance(res[0], QuerySet):
        res = {'results': map(_expand_keys, res[0]),
                'count': res[1],
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

    ret = {'id': report.id, 'title': report.title, 'notes': report.notes,
            'model': report.rmodel, 'public': not bool(report.owner),
            'grammar': rt.getGrammar(request.user.is_staff), 'data': json.loads(report.params)}
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
    report.notes = req_data.get('notes', None)
    report.owner = req_data['owner']
    report.rmodel = req_data['model']
    report.params = json.dumps(req_data['data'])
    report.stage2 = json.dumps(req_data['stage2'])
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
    elif request.method == 'GET':
        # Instead of stage2, we need the pythonic algorithm of the JS part
        # for domains, fields
        report = get_object_or_404(SavedReport.objects.by_request(request), \
                        pk=request.GET.get('id', 0))

        if not report.stage2:
            messages.error(request, _("This report has not been saved properly, no stage2 data"))
            return {}
        report_data = json.loads(report.stage2)
    else:
        return HttpResponseNotAllowed(['POST', 'GET'])

    report_model = report_data.pop('model')
    rt = _reports_cache['main_types'].get(report_model, False)
    if not rt:
        return HttpResponseNotFound("Report type %s not found" % report_model)

    fin = {'report_data': report_data, 'current_time': datetime.datetime.now(),
            'field_cols': report_data.pop('field_cols'),
            'groupped_fields': report_data.pop('groupped_fields'),
        }

    res = rt.getResults(request, **(report_data))
    if isinstance(res, tuple) and isinstance(res[0], QuerySet):
        fin['flat_results'] = map(_expand_keys, res[0])
        fin['have_flat_results'] = True
        fin['count'] = res[1]
    elif isinstance(res, list):
        fin['groupped_results'] = res
        fin['have_groupped_results'] = True
        fin['count'] = res[0]['_count']

    return fin

def reports_results_html(request):
    """Retrieve results, rendered in a html page
    """
    return render(request, 'reports_results.html', _pre_render_report(request))

def reports_results_pdf(request):
    raise NotImplementedError

def csv_fmt(val):
    if val is None:
        return ''
    elif isinstance(val, unicode):
        return val.encode('utf-8')
    elif isinstance(val, bool):
        return (val and 'true') or 'false'
    elif isinstance(val, list):
        return ', '.join(map(csv_fmt, val))
    else:
        # dates?
        return str(val)

def reports_results_csv(request):
    res = _pre_render_report(request)

    if not 'flat_results' in res:
        raise NotImplementedError
    else:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="results.csv"'
        res['field_cols'].sort(key=lambda fc: fc['sequence'])
        fnames = []
        ftitles = []
        for fc in res['field_cols']:
            fnames.append(fc['id'])
            ftitles.append(fc['name'].encode('utf-8'))
        cw = csv.writer(response)
        cw.writerow(ftitles)
        del ftitles
        cw.writerow(fnames)
        for r in res['flat_results']:
            crow = [ csv_fmt(r.get(f)) for f in fnames]
            cw.writerow(crow)
        return response

# eof