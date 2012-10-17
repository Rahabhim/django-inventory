import urllib

from django.core.urlresolvers import reverse, NoReverseMatch
from django.contrib import messages
from django.db.models import Q
from django.db.models.query import QuerySet
from django.db.models.related import RelatedObject
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect, Http404 # , HttpResponse
from django.shortcuts import render_to_response #, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.views.generic.list_detail import object_detail, object_list
from django.views.generic.create_update import delete_object # create_object, update_object, 
import django.views.generic as django_gv
from django.core.exceptions import ImproperlyConfigured
from django.forms.models import inlineformset_factory, ModelForm

from forms import FilterForm, GenericConfirmForm, GenericAssignRemoveForm, \
                  InlineModelForm

def add_filter(request, list_filters):
    filters = []
    filter_dict = dict([(f['name'], f) for f in list_filters])
    if request.method == 'GET':
        filter_form = FilterForm(list_filters, request.GET)
        if filter_form.is_valid():
            for name, data in filter_form.cleaned_data.items():
                if data:
                    filters.append(Q(**{filter_dict[name]['destination']:data}))

    else:
        filter_form = FilterForm(list_filters)

    return filter_form, filters

def generic_list(request, list_filters=[], queryset_filter=None, *args, **kwargs):
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

class GenericCreateView(_InlineViewMixin, django_gv.CreateView):
    template_name = 'generic_form_fs.html'

class GenericUpdateView(_InlineViewMixin, django_gv.UpdateView):
    template_name = 'generic_form_fs.html'

#eof
