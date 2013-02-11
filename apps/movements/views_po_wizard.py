# -*- encoding: utf-8 -*-
import logging
from django.utils.translation import ugettext_lazy as _

from django import forms
from django.shortcuts import render_to_response
from django.contrib.formtools.wizard.views import SessionWizardView
from django.contrib import messages

from common.models import Supplier
from products.models import ItemCategory, Manufacturer, ItemTemplate
from products.form_fields import CategoriesSelectWidget, CategoriesAttributesField
from procurements.models import Contract
from ajax_select.fields import AutoCompleteSelectField #, AutoCompleteSelectMultipleField

from django.db.models import Count
from django.forms.util import ErrorDict
from django.utils.datastructures import MultiValueDict

from models import PurchaseOrder
from weird_fields import DummySupplierWidget, ValidChoiceField, ItemsTreeField, ItemsGroupField

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
    issue_date = forms.DateField(label=_(u'issue date'), required=False)
    
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

    def save(self, commit=True):
        #if not (self.instance.pk or self.instance.create_user_id):
        #    self.instance.create_user = request.user
        return super(PO_Step1, self).save(commit=commit)

class PO_Step2(WizardForm):
    title = _("Select Product Categories")
    new_category = forms.ModelChoiceField(queryset=ItemCategory.objects.filter(approved=True),
            widget=CategoriesSelectWidget)


class PO_Step3(WizardForm):
    title = _("Input Product Details")
    line_num = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    item_template = AutoCompleteSelectField('product_part', label=_("Product"), show_help_text=False, required=False)
    product_number = forms.CharField(max_length=100, required=False, label=_("Product number"))
    quantity = forms.IntegerField(label=_("Quantity"), initial=1)
    serials = forms.CharField(label=_("Serial numbers"), required=False, widget=forms.widgets.Textarea)
    manufacturer = forms.ModelChoiceField(label=_("manufacturer"), queryset=Manufacturer.objects.none(), required=False)
    product_attributes = CategoriesAttributesField(label=_("attributes"), required=False)
    item_template2 = ValidChoiceField(label=_("Product"), choices=(('','------'),), required=False)

    def __init__(self, data=None, files=None, **kwargs):
        super(PO_Step3, self).__init__(data, files, **kwargs)
        if 'product_attributes' in self.initial and 'from_category' in self.initial['product_attributes']:
            # Set the manufacturer according to the existing products of `from_category` ,
            # in descending popularity order
            self.fields['manufacturer'].queryset = Manufacturer.objects.\
                        filter(products__category=self.initial['product_attributes']['from_category']).\
                        annotate(num_products=Count('products')).order_by('-num_products')
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
            step3b_data['3b-ig'] = { 'line_num': our_data['line_num'],
                                    'item_template': our_data['item_template'],
                                    'parts': our_data.get('parts', {}),
                                    }
            wizard.storage.set_step_data('3b', step3b_data)
            return '3b'
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
        # ...
        raise NotImplementedError

class PO_Step3b(WizardForm):
    title = _("Add bundled items")
    step_is_hidden = True

    ig = ItemsGroupField()
    
    def save_data(self, wizard):
        # ...
        step4_data = wizard.storage.get_step_data('4')
        # implementation note: with Session storage, the "getattr(data)" called through
        # get_step_data will set "session.modified=True" and hence what we do below
        # will be preserved
        if step4_data is None:
            step4_data = MultiValueDict()
            
        aitems = step4_data.setdefault('4-items',[])
        our_data = self.cleaned_data.get('ig', {})
        if not our_data.get('line_num', False):
            raise RuntimeError("Step 3b data does not have a line_num from step 3!")
        else:
            for it in aitems:
                if it.get('line_num', False) == our_data['line_num']:
                    assert it.get('item_template') == our_data['item_template'], \
                            "Templates mismatch: %r != %r" % (it.get('item_template'), our_data['item_template'])
                    it['parts'] = our_data['parts']  # in-place
                    break
            else:
                raise RuntimeError("Step 3b data match any line_num at step 4!")
        wizard.storage.set_step_data('4', step4_data)
        wizard.storage.set_step_data('3', {self.add_prefix('quantity'): '1'})
        wizard.storage.set_step_data('3b', {})
        return '4'

class PO_Step3c(WizardForm):
    step_is_hidden = True

class PO_Step4(WizardForm):
    title = _("Final Review")
    items = ItemsTreeField(label=_("Items"), required=False)

class PO_Step5(WizardForm):
    title = _("Successful Entry - Finish")
    subject = forms.CharField(max_length=100, required=False)


class PO_Wizard(SessionWizardView):
    form_list = [('1', PO_Step1), ('2', PO_Step2), ('3', PO_Step3), ('3a', PO_Step3_allo),
            ('3b', PO_Step3b), ('3c', PO_Step3c),
            ('4', PO_Step4),]

    def done(self, form_list, **kwargs):
        return render_to_response('done.html', {
            'form_data': [form.cleaned_data for form in form_list],
        })
    
    @classmethod
    def as_view(cls, **kwargs):
        return super(PO_Wizard,cls).as_view(cls.form_list, **kwargs)

    def get_template_names(self):
        return ['po_wizard_step%s.html' % self.steps.current,]

    def get_context_data(self, form, **kwargs):
        context = super(PO_Wizard, self).get_context_data(form, **kwargs)
        context.update(wiz_steps=self.form_list.items(),
            wiz_width=20)
        return context
    
    def get_form_initial(self, step):
        """
            Feed the `initial` data of step3 with the selection of step2. The
            category is not a field of step3, so we can only communicate the
            value through the `initial` dictionary
        """
        ret = super(PO_Wizard, self).get_form_initial(step)
        if step == '3':
            step2_data =  self.get_cleaned_data_for_step('2') or {}
            ret['product_attributes'] = {'from_category': step2_data.get('new_category', ItemCategory()), 'all': [] }
        return ret

    def get(self, request, *args, **kwargs):
        """ This method handles GET requests.
        
            Unlike the parent WizardView, keep the storage accross GETs and let the
            user continue with previous wizard data.
        """
        # TODO: load PO from kwargs
        return self.render(self.get_form())
    
    def get_form(self, step=None, data=None, files=None):
        if step is None:
            step = self.steps.current
        if step == '4':
            # hack: for step 4, data always comes from the session
            if data and 'iaction' in data:
                if data['iaction'].startswith('edit:'):
                    # push the item's parameters into "data" and bring up the
                    # 3rd wizard page again
                    line_num = int(data['iaction'][5:])
                    old_data = None
                    for item in self.storage.get_step_data(step)['4-items']:
                        if item.get('line_num', -1) == line_num:
                            old_data = item
                            break
                    else:
                        raise IndexError("No line num: %s" % line_num)
                    self.storage.current_step = '3'
                    data = self.storage.get_step_data(self.storage.current_step)
                    data['3-quantity'] = old_data['quantity']
                    data['3-item_template'] = old_data['item_template'].id
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
                    data = self.storage.get_step_data(step)
                    data['4-items'] = filter(lambda it: it.get('line_num', '') != line_num, data['4-items'])
                    self.storage.set_step_data(step, data) # save it immediately
                    form = super(PO_Wizard, self).get_form(step=step, data=data)
                    # invalidate, so that calling function will just render the form
                    if form._errors is None:
                        form._errors = ErrorDict()
                    form._errors[''] = ''
                    return form
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

def get_po_wizview(*args, **kwargs):
    return PO_Wizard.as_view(**kwargs)


#eof
