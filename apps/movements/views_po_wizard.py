# -*- encoding: utf-8 -*-
from django.utils.translation import ugettext as _

from django import forms
from django.shortcuts import render_to_response
from django.contrib.formtools.wizard.views import SessionWizardView

from products.models import ItemCategory
from products.forms import CategoriesMultiSelectWidget
from procurements.models import Contract

class PO_Step1(forms.Form):
    title = _("Purchase Order Header Data")
    user_id = forms.CharField(max_length=32, required=False, label=_(u'purchase order number'))
    #procurement = models.ForeignKey('procurements.Contract', null=True, blank=True, label=_("procurement contract"))
    issue_date = forms.DateField(label=_(u'issue date'), required=False)
    
    contract = forms.ModelChoiceField(label=_("Procurement Contract"), queryset=Contract.objects.all())
    name_or_vat = forms.ChoiceField(label=_('Find by'), widget=forms.widgets.RadioSelect,
            choices=[('vat', _('VAT (exact)')), ('name', _('Company Name'))], )
    name_supplier = forms.CharField(max_length=12, label=_('Company Name'), required=False)
    vat_supplier = forms.CharField(max_length=12, label=_("VAT number"), required=False)

class PO_Step2(forms.Form):
    title = _("Select Product Categories")
    categories = forms.ModelMultipleChoiceField(queryset=ItemCategory.objects.filter(approved=True),
            widget=CategoriesMultiSelectWidget)


class PO_Step3(forms.Form):
    title = _("Input Product Details")
    subject = forms.CharField(max_length=100, required=False)

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

def get_po_wizview(*args, **kwargs):
    return PO_Wizard.as_view(**kwargs)


#eof
