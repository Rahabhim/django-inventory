# -*- encoding: utf-8 -*-
import logging
import datetime
from collections import defaultdict
from operator import itemgetter
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.template import RequestContext

from django import forms
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.contrib.formtools.wizard.views import SessionWizardView
from django.contrib import messages

from common.models import Supplier, Location
from common.api import role_from_request
from company.models import Department
from products.models import ItemCategory, Manufacturer, ItemTemplate
from products.form_fields import CategoriesSelectWidget, CategoriesAttributesField
from procurements.models import Contract
from ajax_select.fields import AutoCompleteSelectField #, AutoCompleteSelectMultipleField

from django.db.models import Count
from django.forms.util import ErrorDict
from django.utils.datastructures import MultiValueDict

from models import PurchaseOrder, Movement
from weird_fields import DummySupplierWidget, ValidChoiceField, ItemsTreeField, ItemsGroupField, GroupGroupField

logger = logging.getLogger('apps.movements.po_wizard')

class _WizardFormMixin:
    title = "Step x"
    step_is_hidden = False

    def save_data(self, wizard):
        pass

class WizardForm(_WizardFormMixin, forms.Form):
    pass

class PO_Step1(_WizardFormMixin, forms.ModelForm):
    title = _("Purchase Order Header Data")
    user_id = forms.CharField(max_length=32, required=False, label=_(u'purchase order number'))
    #procurement = models.ForeignKey('procurements.Contract', null=True, blank=True, label=_("procurement contract"))
    issue_date = forms.DateField(label=_(u'issue date'), required=True)

    procurement = forms.ModelChoiceField(label=_("Procurement Contract"), queryset=Contract.objects.all())
    supplier_name_or_vat = forms.ChoiceField(label=_('Find by'), widget=forms.widgets.RadioSelect,
            initial='name',
            choices=[('vat', _('VAT (exact)')), ('name', _('Company Name'))], )
    supplier_name = AutoCompleteSelectField('supplier_name', label=_("Company Name"), required=False)
    supplier_vat = AutoCompleteSelectField('supplier_vat', label=_("VAT number"), required=False)

    supplier = forms.ModelChoiceField(queryset=Supplier.objects.filter(active=True), widget=DummySupplierWidget)

    class Meta:
        model = PurchaseOrder
        fields = ('user_id', 'issue_date', 'procurement', 'supplier')
                # That's the fields we want to fill in the PO

    def __init__(self, data=None, files=None, **kwargs):
        if kwargs.get('instance', None) is not None:
            initial = kwargs.get('initial', {})
            if not initial.get('supplier_name', None):
                initial['supplier_name'] = kwargs['instance'].supplier_id

        super(PO_Step1, self).__init__(data, files, **kwargs)

    def save_to_db(self, request):
        """ Explicitly commit the data into the database
        """
        if not (self.instance.pk or self.instance.create_user_id):
            self.instance.create_user = request.user
        self.instance.save()

class PO_Step2(WizardForm):
    title = _("Select Product Categories")
    new_category = forms.ModelChoiceField(queryset=ItemCategory.objects.filter(approved=True),
            widget=CategoriesSelectWidget)

    def save_data(self, wizard):
        step3_data = MultiValueDict()
        step3_data['3-quantity'] = 1
        step3_data['3-product_attributes'] = {'from_category': self.cleaned_data['new_category']}
        wizard.storage.set_step_data('3', step3_data)
        return '3'

class PO_Step3(WizardForm):
    title = _("Input Product Details")
    line_num = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    in_group = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    item_template = AutoCompleteSelectField('product_part', label=_("Product"), show_help_text=False, required=False)
    product_number = forms.CharField(max_length=100, required=False, label=_("Product number"))
    quantity = forms.IntegerField(label=_("Quantity"), initial=1)
    serials = forms.CharField(label=_("Serial numbers"), required=False, widget=forms.widgets.Textarea)
    manufacturer = forms.ModelChoiceField(label=_("manufacturer"), queryset=Manufacturer.objects.none(), required=False)
    product_attributes = CategoriesAttributesField(label=_("attributes"), required=False)
    item_template2 = ValidChoiceField(label=_("Product"), choices=(('','------'),), required=False)

    def __init__(self, data=None, files=None, **kwargs):
        super(PO_Step3, self).__init__(data, files, **kwargs)
        pa_pref = self.add_prefix('product_attributes')
        it_pref = self.add_prefix('item_template')
        if data and self.data.get(pa_pref, {}).get('from_category', False):
            # Set the manufacturer according to the existing products of `from_category` ,
            # in descending popularity order
            category = self.data[pa_pref]['from_category']
        elif data and self.data.get(it_pref, {}):
            item = ItemTemplate.objects.get(pk=self.data[it_pref])
            category = item.category
        else:
            category = None
        if category:
            self.fields['manufacturer'].queryset = Manufacturer.objects.\
                        filter(products__category=category).\
                        annotate(num_products=Count('products')).order_by('-num_products')
            self.category_id = category.id
        # self.initial['product_attributes']['all'] = []


    def save_data(self, wizard):
        our_data = self.cleaned_data.copy()
        step4_data = wizard.storage.get_step_data('4')
        # implementation note: with Session storage, the "getattr(data)" called through
        # get_step_data will set "session.modified=True" and hence what we do below
        # will be preserved
        if step4_data is None:
            step4_data = MultiValueDict()
        for ufield in ('product_number', 'manufacturer', \
                        'item_template2', 'product_attributes'):
            our_data.pop(ufield, None)
        aitems = step4_data.setdefault('4-items',[])
        ItemsGroupField.post_validate(our_data)

        if not our_data.get('line_num', False):
            # we have to compute an unique id for the new line_num
            lnmax = 0
            for it in aitems:
                if it.get('line_num', 0) > lnmax:
                    lnmax = it['line_num']
            assert isinstance(lnmax, int), "Not an int, %s: %r" %( type(lnmax), lnmax)
            our_data['line_num'] = lnmax + 1
            our_data['parts'] = {}
            aitems.append(our_data)
        else:
            for it in aitems:
                if it.get('line_num', False) == our_data['line_num']:
                    it.update(our_data) # in-place
                    our_data = it
                    break
            else:
                # line not found
                our_data['parts'] = {}
                aitems.append(our_data)
        wizard.storage.set_step_data('4', step4_data)
        if our_data['item_template'].category.is_bundle:
            step3b_data = MultiValueDict()
            step3b_data['3b-ig'] = our_data.copy()
            wizard.storage.set_step_data('3b', step3b_data)
            return '3b'
        elif our_data['item_template'].category.is_group:
            step3s_data = MultiValueDict()
            step3s_data['3s-iset'] = wizard._make_3sdata(our_data, aitems)
            wizard.storage.set_step_data('3s', step3s_data)
            return '3s'
        elif our_data['in_group']:
            # we are a non-bundle item in a group, return to that group
            # find the group from step4 data
            wizard.storage.set_step_data('3', {self.add_prefix('quantity'): '1'})
            for it in aitems:
                if it.get('line_num', False) == our_data['in_group']:
                    step3s_data = MultiValueDict()
                    step3s_data['3s-iset'] = wizard._make_3sdata(it, aitems)
                    wizard.storage.set_step_data('3s', step3s_data)
                    return '3s'
            # if none found (an error), proceed to step 4!
        else:
            # note: this must also happen after step 3b!
            wizard.storage.set_step_data('3', {self.add_prefix('quantity'): '1'}) # reset this form
        return '4'

class PO_Step3_allo(_WizardFormMixin, forms.ModelForm):
    title = _("New Product Request")
    step_is_hidden = True

    class Meta:
        model = ItemTemplate
        fields = ('description', 'category', 'manufacturer', 'model', 'part_number', 'url', 'notes')

    def save_data(self, wizard):
        self.instance.save()
        wizard.storage.set_step_data('3a', MultiValueDict())
        messages.info(wizard.request, _("Your request for %s has been stored. An administrator of the Helpdesk will review it and come back to you. In the meanwhile, please continue filling the Purchase Order form with the remaining items") % \
                self.instance.description)
        return '4'

class PO_Step3b(WizardForm):
    title = _("Add bundled items")
    step_is_hidden = True

    ig = ItemsGroupField()

    def save_data(self, wizard):
        step4_data = wizard.storage.get_step_data('4')
        # implementation note: with Session storage, the "getattr(data)" called through
        # get_step_data will set "session.modified=True" and hence what we do below
        # will be preserved
        if step4_data is None:
            step4_data = MultiValueDict()

        aitems = step4_data.setdefault('4-items',[])
        our_data = self.cleaned_data.get('ig', {})
        if our_data:
            ItemsGroupField.post_validate(our_data)
        if not our_data.get('line_num', False):
            raise RuntimeError("Step 3b data does not have a line_num from step 3!")
        else:
            for it in aitems:
                if it.get('line_num', False) == our_data['line_num']:
                    assert it.get('item_template') == our_data['item_template'], \
                            "Templates mismatch: %r != %r" % (it.get('item_template'), our_data['item_template'])
                    it['parts'] = our_data['parts']  # in-place
                    it['state'] = our_data.get('state', '')
                    it['errors'] = our_data.get('errors', {})
                    break
            else:
                raise RuntimeError("Step 3b data match any line_num at step 4!")
        if our_data.get('in_group', None):
            # if we are part of a group, don't jump to step 4 but rather return to '3s'
            group_data = False
            for it in aitems:
                if it.get('line_num', None) == our_data['in_group']:
                    group_data = it
            if group_data:
                step3s_data = MultiValueDict()
                step3s_data['3s-iset'] = wizard._make_3sdata(group_data, aitems)
                wizard.storage.set_step_data('3s', step3s_data)
                return '3s'
        wizard.storage.set_step_data('4', step4_data)
        wizard.storage.set_step_data('3', {})
        wizard.storage.set_step_data('3b', {})
        return '4'

class PO_Step3s(WizardForm):
    title = _("Add set items")
    step_is_hidden = True

    iset = GroupGroupField()

    def save_data(self, wizard):
        iset = self.cleaned_data['iset']
        if 'add-groupped' in iset:
            # We need to prepare and jump to step 3, for the "in_group" line
            step3_data = MultiValueDict()
            step3_data['3-quantity'] = 1
            category = ItemCategory.objects.get(pk=iset['add-groupped'])
            step3_data['3-product_attributes'] = {'from_category': category}
            step3_data['3-in_group'] = iset['line_num']
            wizard.storage.set_step_data('3', step3_data)
            return '3'
        # elif 'edit-group' in self.cleaned_data
        else:
            # Normally, there is no data submission with step 3s, so we'd better
            # just clear our data and move on to step 4
            wizard.storage.set_step_data('3', {})
            wizard.storage.set_step_data('3b', {})
            wizard.storage.set_step_data('3s', {})
            return '4'
        raise RuntimeError

class PO_Step4(WizardForm):
    title = _("Final Review")
    items = ItemsTreeField(label=_("Items"), required=False)

    @classmethod
    def prepare_data_from(cls, po_instance):
        """Read the db data from po_instance and populate our special dictionary
        """
        items = []
        for po_item in po_instance.items.all():
            r = {'line_num': po_item.id,
                 'item_template': po_item.item_template,
                 'in_group': po_item.in_group,
                 'quantity': po_item.qty,
                 'serials': po_item.serial_nos,
                 'parts': {},
                 }
            pbc = defaultdict(list) # parts, by category
            for p in po_item.bundled_items.all():
                pbc[p.item_template.category_id].append((p.item_template, p.qty))

            if po_item.item_template.category.is_bundle:
                for mc in po_item.item_template.category.may_contain.all():
                    r['parts'][mc.id] = pbc.pop(mc.category_id, [])

            if pbc:
                logger.warning("Stray parts found for template %s: %r", po_item.item_template, pbc)

            ItemsGroupField.post_validate(r)
            items.append(r)

        ret = MultiValueDict()
        ret['4-items'] = items
        return ret

    def save_data(self, wizard):
        step1 = wizard.get_form(step='1', data=wizard.storage.get_step_data('1'),
                    files=wizard.storage.get_step_files('1'))
        if step1.is_bound and not step1.is_valid():
            # a non-bound form has never received data and therefore
            # cannot be valid. However, we can still save the instance.
            logger.debug("Step 1 is not valid: %r", step1._errors)
            return '1'

        # then save "1", use the instance to save "4"
        step1.save_to_db(wizard.request)
        wizard.storage.extra_data['po_pk'] = step1.instance.pk
        self.save_to_db(wizard.request, step1.instance)
        
        # Validate the bundles and groups
        # Stop at the first error
        errors = False
        line_groups = defaultdict(list)
        for item in self.cleaned_data['items']:
            # check that line is a sensible entry:
            if not item.get('item_template', False):
                logger.debug("Line %s does not have a product", item.get('line_num', 0))
                errors = True
                break
            if not item.get('quantity', 0):
                logger.debug("Line %s does not have quantity", item.get('line_num', 0))
                errors = True
                break
            ItemsGroupField.post_validate(item)
            if item['state'] != 'ok':
                logger.debug("Line %s:%s is %s", item.get('line_num', 0), item['item_template'], item['state'])
                errors = True
                break
            if item['in_group'] and item.get('item_template'):
                line_groups[item['in_group']].append((item['item_template'].category_id, item['quantity']))
        
        if not errors:
            for item in self.cleaned_data['items']:
                if item['item_template'].validate_bundle(line_groups[item['line_num']], flat=True, group_mode=True):
                    # validate returned some errors
                    logger.debug("Line %s:%s failed group validation", item.get('line_num', 0), item['item_template'])
                    errors = True
                    break
        if errors:
            return '4a'
        else:
            step5_data = wizard.storage.get_step_data('5')
            if step5_data is None:
                step5_data = MultiValueDict()
            active_role = role_from_request(wizard.request)
            if active_role:
                step5_data['5-department'] = active_role.department
                wizard.storage.set_step_data('5', step5_data)
            return '5'

    def save_to_db(self, request, po_instance):
        """ Actually save the data in DB (only at this step)
        """
        assert po_instance and po_instance.pk
        items_dict = {}
        for item in self.cleaned_data['items']:
            assert item['line_num'] not in items_dict, "duplicate line!"
            items_dict[item['line_num']] = item

        line_map = {} # map of db.id => "line_num"
        in_group_defer = []
        for po_item in po_instance.items.all():
            item = items_dict.pop(po_item.id, None)
            if item is None:
                po_item.delete()
            else:
                line_map[item['line_num']] = po_item.id
                po_item.item_template = item['item_template']
                po_item.qty = item['quantity']
                if item.get('in_group', None):
                    in_group_defer.append((po_item.id, item['in_group']))
                po_item.in_group = item['in_group']
                po_item.received_qty = po_item.qty
                po_item.serial_nos = item['serials']

                bits = {} # arrange all bundled parts in dict
                          # by part.item_template.id
                for pcats in item.get('parts',{}).values():
                    for p, q in pcats:
                        n = bits.get(p.id, (p, 0))[1]
                        bits[p.id] = (p, n + q)
                for bitem in po_item.bundled_items.all():
                    if bitem.item_template_id not in bits:
                        bitem.delete()
                    else:
                        p, q = bits.pop(bitem.item_template_id)
                        if bitem.qty != q:
                            bitem.qty = q
                            bitem.save()
                for p, q in bits.values():
                    po_item.bundled_items.create(item_template=p, qty=q)

        if items_dict:
            # convert to list again, sort by (fake, yet) id
            items_list2 = items_dict.values()
            items_list2.sort(key=itemgetter('line_num'))
            for item in items_list2:
                po_item = po_instance.items.create(item_template=item['item_template'],
                                qty=item['quantity'], received_qty=item['quantity'],
                                serial_nos=item['serials'])
                if item.get('in_group', None):
                    in_group_defer.append((po_item.id, item['in_group']))
                line_map[item['line_num']] = po_item.id
                for pcats in item.get('parts',{}).values():
                    for p, q in pcats:
                        po_item.bundled_items.create(item_template=p, qty=q)
        if in_group_defer:
            for pk, grp_line in in_group_defer:
                contained = po_instance.items.get(pk=pk)
                group_pk = line_map.get(grp_line, None)
                if not group_pk:
                    logger.warning("Algo failure: cannot locate group %s", grp_line)
                    continue
                contained.in_group = group_pk
                contained.save()
        return

class PO_Step4a(WizardForm):
    step_is_hidden = True
    title = _("Pending Items - Finish")


class PO_Step5(WizardForm):
    title = _("Successful Entry - Finish")
    department = forms.ModelChoiceField(queryset=Department.objects.all(), widget=forms.widgets.HiddenInput, required=False)
    location = forms.ModelChoiceField(label=_("location"), widget=forms.widgets.RadioSelect,
                    queryset=Location.objects.none())

    def __init__(self, data=None, files=None, **kwargs):
        super(PO_Step5, self).__init__(data, files, **kwargs)
        if data and data.get('5-department', None):
            dept = data['5-department']
        else:
            dept = Department.objects.filter(deprecate=False, location__isnull=False)[:1][0]
            logger.warning("Using an arbitrary department: #%s %s !", dept.id, dept.name)
        self.fields['location'].queryset = Location.objects.filter(department=dept)

    def save_data(self, wizard):
        # Mostly copied from views.purchase_order_receive
        po_instance = wizard.get_form_instance('1')
        request = wizard.request
        if not po_instance.pk:
            raise RuntimeError("PO instance must be saved by step 5")
        try:
            items_left = po_instance.calc_unmoved_items()
        except ValueError, ve:
            messages.error(request, unicode(ve), fail_silently=True)
            return '5'

        active_role = None
        msg = None
        try:
            active_role = role_from_request(request)
        except ObjectDoesNotExist:
            pass

        if items_left:
            if not active_role.has_perm('movements.receive_purchaseorder'):
                raise PermissionDenied
            lsrcs = Location.objects.filter(department__isnull=True, usage='procurement')[:1]
            lbdls = Location.objects.filter(department__isnull=True, usage='production')[:1]
            ldests = [self.cleaned_data['location'],]
            if not lsrcs:
                msg = _(u'There is no procurement location configured in the system!')
                messages.error(request, msg, fail_silently=True)
            elif not ldests:
                msg = _(u'This is not default department and location for this user, please fix!')
                messages.error(request, msg, fail_silently=True)
            elif not lbdls:
                msg = _(u'This is not bundling location configured in the system!')
                messages.error(request, msg, fail_silently=True)
            else:
                movement = Movement(create_user=request.user, date_act=datetime.date.today(),
                        stype='in', origin=po_instance.user_id,
                        location_src=lsrcs[0], location_dest=ldests[0],
                        purchase_order=po_instance)
                movement.save()
                bundled = po_instance.fill_out_movement(items_left, movement)
                if bundled:
                    # print "must put a few items in bundle, too"
                    movement = Movement(create_user=request.user, date_act=datetime.date.today(),
                        stype='in', origin=po_instance.user_id,
                        location_src=lsrcs[0], location_dest=lbdls[0],
                        purchase_order=po_instance)
                    movement.save()
                    po_instance.fill_out_bundle_move(bundled, movement)
        
        if msg:
            return '5'

class PO_Wizard(SessionWizardView):
    form_list = [('1', PO_Step1), ('2', PO_Step2), ('3', PO_Step3), ('3a', PO_Step3_allo),
            ('3s', PO_Step3s), ('3b', PO_Step3b),
            ('4', PO_Step4), ('4a', PO_Step4a), ('5', PO_Step5)]


    @classmethod
    def as_view(cls, **kwargs):
        """ Hard-code the form_list in the constructor.
        """
        return super(PO_Wizard,cls).as_view(cls.form_list, **kwargs)

    def get_template_names(self):
        return ['po_wizard_step%s.html' % self.steps.current,]

    def get_context_data(self, form, **kwargs):
        """ Add the wizard steps counter into the context
        """
        context = super(PO_Wizard, self).get_context_data(form, **kwargs)
        context.update(wiz_steps=self.form_list.items(),
            wiz_width=16)
        return context

    def get_form_instance(self, step):
        """ Load the PurchaseOrder instance for step1, from the primary key
        """
        if step == '1' and 'po_pk' in self.storage.extra_data:
            try:
                return PurchaseOrder.objects.get(pk=self.storage.extra_data['po_pk'])
            except PurchaseOrder.DoesNotExist:
                pass
        return super(PO_Wizard, self).get_form_instance(step)

    def get(self, request, *args, **kwargs):
        """ This method handles GET requests.

            Unlike the parent WizardView, keep the storage accross GETs and let the
            user continue with previous wizard data.

            BUT, if we are called with `object_id=123` , that means we need to reset
            the storage, load an existing PO and edit that instead. We do all the
            loading into the storage and then redirect to the persistent wizard.
        """
        if 'object_id' in kwargs:
            # code from super().get() :
            self.storage.reset()
            # Start from step 4!
            self.storage.current_step = '4' # rather than: self.steps.first

            po_instance = get_object_or_404(PurchaseOrder, pk=kwargs['object_id'])
            self.storage.extra_data = {'po_pk': po_instance.id }
            # Loading the instance into step1's data is hard, so we defer to
            # get_form_instance(step=1) instead

            # But, we can do the pre-processing of step4 here:
            self.storage.set_step_data('4', self.form_list['4'].prepare_data_from(po_instance))

            return redirect('purchaseorder_wizard') # use the plain url, that won't reset again
        elif kwargs.get('new', False):
            # just reset the data..
            self.storage.reset()
            return redirect('purchaseorder_wizard')

        return self.render(self.get_form())

    def get_form(self, step=None, data=None, files=None):
        if step is None:
            step = self.steps.current
        if step in ('4', '3s'):
            # edit actions of items
            if data and 'iaction' in data:
                if data['iaction'].startswith('edit:'):
                    # push the item's parameters into "data" and bring up the
                    # 3rd wizard page again
                    line_num = int(data['iaction'][5:])
                    old_data = None
                    for item in self.storage.get_step_data('4')['4-items']:
                        if item.get('line_num', 'foo') == line_num:
                            old_data = item
                            break
                    else:
                        raise IndexError("No line num: %s" % line_num)
                    if old_data['item_template'].category.is_group:
                        # a group cannot be edited.
                        # Instead, we proceed to step 3s to edit its contents
                        self.storage.current_step = '3s'
                        data = self.storage.get_step_data(self.storage.current_step)
                        if data is None:
                            data = MultiValueDict()
                        data['3s-iset'] = self._make_3sdata(old_data, False)
                        form = super(PO_Wizard, self).get_form(step='3s', data=data)
                        if form._errors is None:
                            form._errors = ErrorDict()
                        form._errors[''] = ''
                        return form
                    # else, goto step 3:
                    self.storage.current_step = '3'
                    data = self.storage.get_step_data(self.storage.current_step)
                    if data is None:
                        data = MultiValueDict()
                    data['3-quantity'] = old_data['quantity']
                    data['3-item_template'] = old_data['item_template'].id
                    data['3-in_group'] = old_data.get('in_group', None)
                    data['3-serials'] = old_data['serials']
                    if 'line_num' in old_data:
                        data['3-line_num'] = int(old_data['line_num'])
                    form = super(PO_Wizard, self).get_form(step='3', data=data)
                    # invalidate, so that calling function will just render the form
                    if form._errors is None:
                        form._errors = ErrorDict()
                    form._errors[''] = ''
                    return form
                elif data['iaction'].startswith('delete:'):
                    line_num = data['iaction'][7:]
                    if line_num:
                        # only convert if non-empty
                        line_num = int(line_num)
                    # switch to stored data:
                    data4 = self.storage.get_step_data('4')
                    data4['4-items'] = filter(lambda it: it.get('line_num', '') != line_num, data4['4-items'])
                    self.storage.set_step_data('4', data4) # save it immediately
                    if step == '3s':
                        # update the data for 3s
                        old_data = None
                        line_num = int(data['id_3s-iset_line_num'])
                        for it in data4['4-items']:
                            if it.get('line_num', None) == line_num:
                                old_data = it
                        data = data.copy()
                        data['3s-iset'] = self._make_3sdata(old_data, data4['4-items'])
                    else:
                        data = data4
                    form = super(PO_Wizard, self).get_form(step=step, data=data)
                    # invalidate, so that calling function will just render the form
                    if form._errors is None:
                        form._errors = ErrorDict()
                    form._errors[''] = ''
                    return form
        if step == '4':
            # hack: for step 4, data always comes from the session
            data = self.storage.get_step_data(step)
        return super(PO_Wizard, self).get_form(step=step, data=data, files=files)

    def render_next_step(self, form, **kwargs):
        """
        This method gets called when the next step/form should be rendered.
        `form` contains the last/current form.
        """
        try:
            next_step = form.save_data(self)
        except Exception, e:
            messages.error(self.request, _('Cannot save data'))
            logger.exception('cannot save at step %s: %s' % (self.steps.current, e))
            return self.render(form)

        # get the form instance based on the data from the storage backend
        # (if available).
        if next_step is None:
            next_step = self.steps.next

        new_form = self.get_form(next_step,
            data=self.storage.get_step_data(next_step),
            files=self.storage.get_step_files(next_step))

        # change the stored current step
        self.storage.current_step = next_step
        return self.render(new_form, **kwargs)

    def render_done(self, form, **kwargs):
        # First, prepare forms 1 and 4 and validate them:
        try:
            res = form.save_data(self)
        except Exception, e:
            messages.error(self.request, _('Cannot save data'))
            logger.exception('cannot finish at step %s: %s' % (self.steps.current, e))
            return self.render(form)
        if res:
            self.render_revalidation_failure(self.steps.current, form, **kwargs)
        return redirect('purchase_order_pending_list')

    def _make_3sdata(self, data3, aitems):
        """Prepare the data structure for step 3s

            The 3s structure has a full item (including `item_template` and `line_num`),
            as well as the `contents`.
        """
        if not aitems:
            step4_data = self.storage.get_step_data('4')
            if step4_data is None:
                step4_data = MultiValueDict()
            aitems = step4_data.setdefault('4-items',[])
        ret = dict(data3, contents=[])
        line_num = ret['line_num']
        for it in aitems:
            if it.get('in_group', None) == line_num:
                ret['contents'].append(it)
        return ret
#eof