import urllib

from django.core.urlresolvers import reverse, NoReverseMatch
from django.contrib import messages
from django.db.models import Q
from django.db.models.query import QuerySet
from django.db.models.related import RelatedObject
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.views.generic.list_detail import object_detail, object_list
from django.views.generic.create_update import create_object, update_object, delete_object
import django.views.generic as django_gv
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.forms.models import inlineformset_factory, ModelForm

from forms import FilterForm, GenericConfirmForm, GenericAssignRemoveForm, \
                  InlineModelForm, DetailForm
import logging

def add_filter(request, list_filters):
    """ Add list filters to form and eventually filter the queryset

        @param list_filter a list of dicts, each describing a filter

        A filter can have the following items:
            'name' required, the field name in the html form
            'destination' required, the field filter name. It can be a string like
                        "name__icontains", a plain field like "manufacturer" or
                        a list/tuple of strings, that will be OR-ed together
                        If it is a callable, it will be called like fn(data)
                        and expected to return a Q() filter-expression
            'queryset' optional, if set, it will be a ModelChoice form (selection) with
                    the queryset records as options
            'lookup_channel': optional, if set, it will present an AutoComplete for that
                    completion "channel"
    """
    filters = []
    filter_dict = dict([(f['name'], f) for f in list_filters])
    if request.method == 'GET':
        filter_form = FilterForm(list_filters, request.GET)
        if filter_form.is_valid():
            for name, data in filter_form.cleaned_data.items():
                if not data:
                    continue
                dest = filter_dict[name]['destination']
                if isinstance(dest, basestring):
                    filters.append(Q(**{dest:data}))
                elif isinstance(dest, (tuple, list)):
                    q = None
                    for idest in dest:
                        nq = Q(**{idest:data})
                        if q is None:
                            q = nq
                        else:
                            q = q | nq
                    filters.append(q)
                elif callable(dest):
                    q = dest(data)
                    if not isinstance(q, Q):
                        raise TypeError("Callable at filter %s returned a %s" % (name, type(q)))
                    filters.append(q)
                else:
                    raise TypeError("invalid destination: %s" % type(dest))

    else:
        filter_form = FilterForm(list_filters)
            
    return filter_form, filters

def generic_list(request, list_filters=[], queryset_filter=None, *args, **kwargs):
    """
        Remember that choice fields may need the "get_FOO_display" method rather than
        a direct value of "FOO".
    """
    filters = None
    if list_filters:
        filter_form, filters = add_filter(request, list_filters)
        kwargs['extra_context']['filter_form'] = filter_form

    if 'queryset' in kwargs and not isinstance(kwargs['queryset'], QuerySet) \
                and callable(kwargs['queryset']):
        queryset_fn = kwargs.pop('queryset')
        # since we evaluate the queryset here, this breaks the caching and
        # allows different result set per request (as desired).
        # Otherwise, the queryset would be queried once in db and reused
        # across requests, with same rows.
        kwargs['queryset'] = queryset_fn(request)

    if filters:
        kwargs['queryset'] = kwargs['queryset'].filter(*filters)
        
    return object_list(request,  template_name='generic_list.html', *args, **kwargs)

def generic_delete(*args, **kwargs):
    try:
        kwargs['post_delete_redirect'] = reverse(kwargs['post_delete_redirect'])
    except NoReverseMatch:
        pass

    if 'extra_context' in kwargs:
        kwargs['extra_context']['delete_view'] = True
    else:
        kwargs['extra_context'] = {'delete_view':True}
  
    return delete_object(template_name='generic_confirm.html', *args, **kwargs)

def generic_confirm(request, _view, _title=None, _model=None, _object_id=None, _message='', *args, **kwargs):
    if request.method == 'POST':
        form = GenericConfirmForm(request.POST)
        if form.is_valid():
            if hasattr(_view, '__call__'):
                return _view(request, *args, **kwargs)
            else:
                return HttpResponseRedirect(reverse(_view, args=args, kwargs=kwargs))

    data = {}
    
    try:
        object = _model.objects.get(pk=kwargs[_object_id])
        data['object'] = object
    except:
        pass
    
    try:
        data['title'] = _title
    except:
        pass

    try:
        data['message'] = _message
    except:
        pass

    form=GenericConfirmForm()
        
    return render_to_response('generic_confirm.html',
        data,
        context_instance=RequestContext(request))	

def generic_assign_remove(request, title, obj, left_list_qryset, left_list_title, right_list_qryset, right_list_title, add_method, remove_method, item_name, list_filter=None):
    left_filter = None
    filter_form = None
    if list_filter:
        filter_form, filters = add_filter(request, list_filter)
        if filters:
            left_filter = filters
            

    if request.method == 'POST':
        post_data = request.POST
        form = GenericAssignRemoveForm(left_list_qryset, right_list_qryset, left_filter, request.POST)
        if form.is_valid():
            action = post_data.get('action','')
            if action == "assign":
                for item in form.cleaned_data['left_list']:
                    add_method(item)
                if form.cleaned_data['left_list']:
                    messages.success(request, _(u"The selected %s were added.") % unicode(item_name))

            if action == "remove":
                for item in form.cleaned_data['right_list']:
                    remove_method(item)
                if form.cleaned_data['right_list']:
                    messages.success(request, _(u"The selected %s were removed.") % unicode(item_name))

    form = GenericAssignRemoveForm(left_list_qryset=left_list_qryset, right_list_qryset=right_list_qryset, left_filter=left_filter)
        
    return render_to_response('generic_assign_remove.html', {
    'form':form,
    'object':obj,
    'title':title,
    'left_list_title':left_list_title,
    'right_list_title':right_list_title,
    'filter_form':filter_form,
    },
    context_instance=RequestContext(request))


def generic_detail(request, object_id, form_class, queryset, title=None, extra_context={}, extra_fields=[]):
    #if isinstance(form_class, DetailForm):
    if queryset is not None and not isinstance(queryset, QuerySet) \
                and callable(queryset):
        queryset = queryset(request)

    try:
        if extra_fields:
            form = form_class(instance=queryset.get(id=object_id), extra_fields=extra_fields)
        else:
            form = form_class(instance=queryset.get(id=object_id))
    except ObjectDoesNotExist:
        raise Http404
    
    extra_context['form'] = form
    extra_context['title'] = title
   
    return object_detail(
        request,
        template_name='generic_detail.html',
        extra_context=extra_context,
        queryset=queryset,
        object_id=object_id,
    )


class _InlineViewMixin(object):
    extra_context = None
    inline_fields = ()
    _inline_formsets = None

    def __init__(self, **kwargs):
        super(_InlineViewMixin, self).__init__(**kwargs)
        if not self.model:
            form_class = self.get_form_class()
            if form_class:
                self.model = form_class._meta.model
            elif hasattr(self, 'object') and self.object is not None:
                self.model = self.object.__class__

        self._inline_formsets = {}
        infields = self.inline_fields
        if isinstance(infields, (tuple, list)):
            infields = dict.fromkeys(infields, InlineModelForm)
        for inlf, iform_class in infields.items():
            relo = self.model._meta.get_field_by_name(inlf)
            if not isinstance(relo[0], RelatedObject):
                raise ImproperlyConfigured("Field %s.%s is not a related object for inlined field of %s" % \
                    (self.model._meta.object_name, inlf, self.__class__.__name__))
            self._inline_formsets[inlf] = inlineformset_factory(self.model, \
                            relo[0].model, form=iform_class, extra=1)
            # explicitly set this (new) attribute, because jinja2 is not allowed to see '_meta'
            self._inline_formsets[inlf].title = relo[0].model._meta.verbose_name_plural

    def form_valid(self, form):
        if hasattr(form, '_pre_save_by_user'):
            form._pre_save_by_user(self.request.user)
        context = self.get_context_data()
        if all([ inline_form.is_valid() for inline_form in context['formsets']]):
            self.object = form.save()
            for inline_form in context['formsets']:
                inline_form.instance = self.object
                inline_form.save()
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super(_InlineViewMixin, self).get_context_data(**kwargs)

        if self.request.POST:
            iargs = (self.request.POST, self.request.FILES)
        else:
            iargs =()

        context['formsets'] = []
        for inlf in self.inline_fields:
            context['formsets'].append(self._inline_formsets[inlf](*iargs))
        if self.extra_context:
            context.update(self.extra_context)
        return context

    def get_form(self, form_class):
        form = super(_InlineViewMixin, self).get_form(form_class)
        if hasattr(form, '_init_by_user'):
            form._init_by_user(self.request.user)
        return form

    def get_success_url(self):
        if callable(self.success_url):
            return self.success_url(self.object)
        else:
            return super(_InlineViewMixin, self).get_success_url()

class _PermissionsMixin(object):
    need_permission = False
    _logger = logging.getLogger('permissions')

    def dispatch(self, request, *args, **kwargs):
        if self.need_permission:
            npd = {}
            model = False
            if hasattr(self, 'model'):
                 model= self.model
            elif hasattr(self, 'form_class'):
                model = self.form_class._meta.model
            if model:
                npd['app'] = model._meta.app_label
                npd['Model'] = model._meta.object_name
                npd['model'] = model._meta.module_name
            np = self.need_permission
            np = np % npd
            if not request.user.has_perm(np):
                self._logger.warning("%s view denied %s permission to user %s",
                        self.__class__.__name__, np, request.user.name)
                raise PermissionDenied
        return super(_PermissionsMixin, self).dispatch(request, *args, **kwargs)

class GenericCreateView(_PermissionsMixin, _InlineViewMixin, django_gv.CreateView):
    template_name = 'generic_form_fs.html'
    need_permission = '%(app)s.add_%(model)s'

class GenericUpdateView(_PermissionsMixin, _InlineViewMixin, django_gv.UpdateView):
    template_name = 'generic_form_fs.html'
    need_permission = '%(app)s.change_%(model)s'

class GenericDetailView(_InlineViewMixin, django_gv.DetailView):
    """ Form-based, read-only view of an object
    """
    template_name = 'generic_detail.html'
    form_mode = 'details'
    form_class = DetailForm
    extra_fields = None

    def get_queryset(self):
        if self.queryset is not None and not isinstance(self.queryset, QuerySet) \
                    and callable(self.queryset):
            return self.queryset(self.request)
        else:
            return super(GenericDetailView, self).get_queryset()

    def get_context_data(self, **kwargs):
        ret = super(GenericDetailView, self).get_context_data(**kwargs)
        # a little weird that we're making the form after the formsets. But we
        # must call get_form() after get_context_data() initializes self.object
        assert 'form' not in ret, ret.get('form', False )
        form_class = self.get_form_class()
        ret['form'] = self.get_form(form_class)
        return ret

    def get_form_class(self):
        return self.form_class

    def get_form(self, form_class):
        """
        Returns an instance of the form to be used in this view.
        """
        assert self.object
        try:
            if self.extra_fields:
                form = form_class(instance=self.object, extra_fields=self.extra_fields)
            else:
                form = form_class(instance=self.object)
        except ObjectDoesNotExist:
            raise Http404
        return form

#eof
