# -*- encoding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, render_to_response, get_object_or_404
from django.http import HttpResponseNotFound, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.utils.functional import Promise
from django.db import models
from django.db.models.query import QuerySet
import json
from django.utils.safestring import SafeString

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

    def real_init(self):
        pass

    def getGrammar(self):
        return {'name': self.title, 'sequence': self.sequence }

    def getQuery(self, name, domain):
        """Constructs a Django Q object, according to `domain` (as from client)

            @param name field name
        """
        raise NotImplementedError

    def to_main_report(self, idn):
        ret = {'id': idn, 'name': self.title, 'sequence': self.sequence }
        if getattr(self, 'famfam_icon', None):
            ret['famfam'] = 'famfam-' + self.famfam_icon

        return ret

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
            self.title = self._model_inst._meta.verbose_name_plural

    def getGrammar(self):
        ret = super(CJFilter_Model, self).getGrammar()
        ret['widget'] = 'model'
        ret['fields'] = {}
        for k, field in self.fields.items():
            ret['fields'][k] = field.getGrammar()
        return ret

class CJFilter_Product(CJFilter_Model):

    def getGrammar(self):
        ret = super(CJFilter_Product, self).getGrammar()
        ret['widget'] = 'model-product'
        return ret

class CJFilter_String(CJFilter):
    sequence = 9

    def getGrammar(self):
        ret = super(CJFilter_String, self).getGrammar()
        ret['widget'] = 'char'
        return ret

class CJFilter_lookup(CJFilter_Model):
    """Select *one* of some related model, with an autocomplete field
    """

    def __init__(self, model, lookup, **kwargs):
        self.lookup = lookup
        self.fields = {}
        super(CJFilter_lookup, self).__init__(model, **kwargs)

    def getGrammar(self):
        ret = super(CJFilter_lookup, self).getGrammar()
        del ret['fields']
        ret['widget'] = 'lookup'
        ret['lookup'] = reverse('ajax_lookup', args=[self.lookup,])
        return ret

class CJFilter_contains(CJFilter):
    """ Filter for an array that must contain *all of* the specified criteria

        "sub" is the filter for each of the criteria, but will be repeated N times
        and request to satisfy all of those N contents.
    """
    def __init__(self, sub_filter, **kwargs):
        assert isinstance(sub_filter, CJFilter), repr(sub_filter)
        self.sub = sub_filter
        super(CJFilter_contains, self).__init__(**kwargs)

    def getGrammar(self):
        ret = super(CJFilter_contains, self).getGrammar()
        ret['widget'] = 'contains'
        ret['sub'] = self.sub.getGrammar()
        return ret

class CJFilter_attribs(CJFilter_Model):
    #def __init__(self, sub_filter, **kwargs):
    #    assert isinstance(sub_filter, CJFilter), repr(sub_filter)
    #    self.sub = sub_filter
    #    super(CJFilter_contains, self).__init__(**kwargs)

    def getGrammar(self):
        ret = super(CJFilter_attribs, self).getGrammar()
        ret['widget'] = 'attribs'
        # ret['sub'] = self.sub.getGrammar()
        return ret


location_filter = CJFilter_Model('common.Location')
manuf_filter = CJFilter_lookup('products.Manufacturer', 'manufacturer')

product_filter = CJFilter_Product('products.ItemTemplate',
    sequence=20,
    fields = {
            'name': CJFilter_String(title=_('name'), sequence=1),
            'category': CJFilter_lookup('products.ItemCategory', 'categories', sequence=5),
            'manufacturer': manuf_filter,
            'attributes': CJFilter_attribs('products.ItemTemplateAttributes', sequence=15),
            }
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
            'item_group': CJFilter_contains(item_templ_c_filter, title=_('containing'), sequence=25),
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
            }

    _reports_cache['available_types'] = [ rt.to_main_report(k) for k, rt in _reports_cache['main_types'].items()]

# ------------------ Views -------------

def reports_app_view(request, object_id=None):
    _reports_init_cache()
    return render(request, 'reports_app.html',
            {'available_types': SafeString(json.dumps(_reports_cache['available_types'], cls=JsonEncoderS)),
            })

def reports_parts_params_view(request, part_id):
    _reports_init_cache()
    if part_id not in _reports_cache['main_types']:
        return HttpResponseNotFound("Part for type %s not found" % part_id)
    
    return render(request, 'params-%s.html' % part_id, {})

def reports_grammar_view(request, rep_type):
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

# eof