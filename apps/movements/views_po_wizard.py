# -*- encoding: utf-8 -*-
from django.utils.translation import ugettext as _

from django import forms
from django.shortcuts import render_to_response
from django.contrib.formtools.wizard.views import SessionWizardView

from products.models import ItemCategory, Manufacturer
from products.form_fields import CategoriesSelectWidget, CategoriesAttributesField
from procurements.models import Contract
from ajax_select.fields import AutoCompleteSelectField, AutoCompleteSelectMultipleField
from django.db.models import Count

class PO_Step1(forms.Form):
    title = _("Purchase Order Header Data")
    user_id = forms.CharField(max_length=32, required=False, label=_(u'purchase order number'))
    #procurement = models.ForeignKey('procurements.Contract', null=True, blank=True, label=_("procurement contract"))
    issue_date = forms.DateField(label=_(u'issue date'), required=False)
    
    contract = forms.ModelChoiceField(label=_("Procurement Contract"), queryset=Contract.objects.all())
    name_or_vat = forms.ChoiceField(label=_('Find by'), widget=forms.widgets.RadioSelect,
            initial='name',
            choices=[('vat', _('VAT (exact)')), ('name', _('Company Name'))], )
    name_supplier = AutoCompleteSelectField('supplier_name', label=_("Company Name"), required=False)
    vat_supplier = AutoCompleteSelectField('supplier_vat', label=_("VAT number"), required=False)

class PO_Step2(forms.Form):
    title = _("Select Product Categories")
    new_category = forms.ModelChoiceField(queryset=ItemCategory.objects.filter(approved=True),
            widget=CategoriesSelectWidget)


class PO_Step3(forms.Form):
    title = _("Input Product Details")
    item_template = AutoCompleteSelectField('product', label=_("Product"), show_help_text=False, required=False)
    product_number = forms.CharField(max_length=100, required=False, label=_("Product number"))
    quantity = forms.IntegerField(label=_("Quantity"), initial=1)
    serials = forms.CharField(label=_("Serial numbers"), required=False, widget=forms.widgets.Textarea)
    manufacturer = forms.ModelChoiceField(label=_("manufacturer"), queryset=Manufacturer.objects.none(), required=False)
    product_attributes = CategoriesAttributesField(label=_("attributes"), required=False)
    item_template2 = forms.ChoiceField(label=_("Product"), choices=(('','------'),), required=False)

    def __init__(self, data=None, files=None, **kwargs):
        super(PO_Step3, self).__init__(data, files, **kwargs)
        if 'product_attributes' in self.initial and 'from_category' in self.initial['product_attributes']:
            # Set the manufacturer according to the existing products of `from_category` ,
            # in descending popularity order
            self.fields['manufacturer'].queryset = Manufacturer.objects.\
                        filter(products__category=self.initial['product_attributes']['from_category']).\
                        annotate(num_products=Count('products')).order_by('-num_products')
        # self.initial['product_attributes']['all'] = []

class PO_Step4(forms.Form):
    title = _("Final Review")
    subject = forms.CharField(max_length=100, required=False)

class PO_Step5(forms.Form):
    title = _("Successful Entry - Finish")
    subject = forms.CharField(max_length=100, required=False)


class PO_Wizard(SessionWizardView):
    form_list = [('1', PO_Step1), ('2', PO_Step2), ('3', PO_Step3), ('4', PO_Step4), ('5', PO_Step5)]

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
            wiz_width=(100/len(self.form_list)))
        return context
    
    def get_form_initial(self, step):
        ret = super(PO_Wizard, self).get_form_initial(step)
        if step == '3':
            step2_data =  self.get_cleaned_data_for_step('2')
            ret['product_attributes'] = {'from_category': step2_data.get('new_category', None), 'all': [] }
        return ret

def get_po_wizview(*args, **kwargs):
    return PO_Wizard.as_view(**kwargs)


#eof
