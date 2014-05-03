# -*- encoding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, render_to_response, get_object_or_404
from django.http import HttpResponseNotFound, HttpResponse
from django.template import RequestContext
from django.utils.functional import Promise
from django.db import models
import json
from django.utils.safestring import SafeString

class JsonEncoderS(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return unicode(obj)
        return super(JsonEncoderS, self).default(obj)

# ----------- Filters ----------------

class CJFilter(object):
    """Base for some search criterion, represents a search field
    """
    title = ''
    _instances = []

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        CJFilter._instances.append(self)

    def real_init(self):
        pass

    def getGrammar(self):
        return {'name': self.title }

    def getQuery(self, name, domain):
        """Constructs a Django Q object, according to `domain` (as from client)

            @param name field name
        """
        raise NotImplementedError
    
    def to_main_report(self, idn):
        ret = {'id': idn, 'name': self.title }
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

class CJFilter_String(CJFilter):
    pass

    def getGrammar(self):
        ret = super(CJFilter_String, self).getGrammar()
        ret['widget'] = 'char'
        return ret


location_filter = CJFilter_Model('common.Location')
manuf_filter = CJFilter_Model('products.Manufacturer')
manuf_filter.fields['name'] = CJFilter_String(title=_('name'))

product_filter = CJFilter_Model('products.ItemTemplate',
    fields = {
            'name': CJFilter_String(title=_('name')),
            'manufacturer': manuf_filter,
            }
    )

item_templ_filter = CJFilter_Model('assets.Item', title=_('asset'),
    fields = {
            'location': location_filter,
            'item_template': product_filter,
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

# eof