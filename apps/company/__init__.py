# -*- encoding: utf-8 -*-
# Copyright P. Christeas <xrg@hellug.gr> 2012
# Only a few rights reserved
from django.utils.translation import ugettext_lazy as _
from common.api import register_links, register_menu

register_menu([
    {'text':_('company'), 'view':'company_department_list', 'links':[
        #purchase_request_list, purchase_order_list,
    ],'famfam':'basket','position':3}]) # FIXME: icon

#eof