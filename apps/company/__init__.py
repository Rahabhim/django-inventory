# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from common.api import register_links, register_menu
from common import location_list

import models
from lookups import _department_filter_q

department_type_filter = {'name':'department_type', 'title':_(u'type'), 'queryset': models.DepartmentType.objects.all(), 'destination':'dept_type'}

department_assets = {'text':_(u'assets'), 'view':'department_assets', 'args':'object.id', 'famfam':'computer'}

def make_mv_location(destination):
    """ Constructs the filter clojure for a destination column
    """
    dept_col = destination + '__department__in'
    dept_col2 = destination + '__department__isnull'
    lname_col = destination + '__name__icontains'
    return lambda q: Q(**{dept_col: models.Department.objects.filter(_department_filter_q(q))}) | \
                    Q(**{dept_col2:True, lname_col: q})


register_menu([
    {'text':_('company'), 'view':'company_department_list', 
            'links':[ {'text':_('departments'), 'view':'company_department_list', 'famfam':'page_go'},
                {'text':_('department types'), 'view':'company_department_type_list', 'famfam':'page_go'},
                location_list,
                ],
        'famfam':'building','position':4}])

register_links(models.Department, [department_assets,])

#eof