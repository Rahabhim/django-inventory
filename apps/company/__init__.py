# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from common.api import register_links, register_menu, user_is_staff, user_is_super
from common import location_list, location_tmpl_list

import models
from lookups import _department_filter_q

department_type_filter = {'name':'department_type', 'title':_(u'type'), 'queryset': models.DepartmentType.objects.all(), 'destination':'dept_type'}

department_assets = {'text':_(u'assets'), 'view':'department_assets', 'args':'object.id', 'famfam':'computer'}

department_update = {'text':_(u'edit department'), 'view':'department_update',
            'args':'object.id', 'famfam':'pencil', 'condition': user_is_super}

def make_mv_location(*dests):
    """ Constructs the filter clojure for a destination column
    """
    # dept_col2 = destination + '__department__isnull'
    dds = []
    for d in dests:
        dds.append((d + '__department__in', lambda q: models.Department.objects.filter(_department_filter_q(q)) ))
        dds.append((d + '__name__icontains', lambda q: q ))

    def ret_fn(q):
        qs = []
        for dd_k, dd_l in dds:
            qs.append(Q(**{dd_k : dd_l(q) }))
        return reduce(lambda a, b: a | b, qs)
    return ret_fn

company_department_list = {'text':_('departments'), 'view':'company_department_list', 'famfam':'page_go'}
company_department_type_list = {'text':_('department types'), 'view':'company_department_type_list', 'famfam':'page_go'}

register_menu([
    {'text':_('company'), 'view':'company_department_list', 
            'links':[ company_department_list, company_department_type_list, location_list, location_tmpl_list ],
        'famfam':'building','position':4, 'condition': user_is_staff}])

register_links(models.Department, [department_assets, department_update])

#eof