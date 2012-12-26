# -*- encoding: utf-8 -*-
from django.utils.translation import ugettext as _

from django import forms
from django.shortcuts import render_to_response
from django.contrib.formtools.wizard.views import SessionWizardView

class PO_Step1(forms.Form):
    user_id = forms.CharField(max_length=32, required=False, label=_(u'purchase order number'))
    #procurement = models.ForeignKey('procurements.Contract', null=True, blank=True, label=_("procurement contract"))
    #supplier = models.ForeignKey(Supplier, label=_(u'supplier'))
    issue_date = forms.DateField(label=_(u'issue date'))
    vat_number = forms.CharField(max_length=12, label=_("VAT number"))

class PO_Step2(forms.Form):
    #categories = forms.SomeField()
    pass

class PO_Step3(forms.Form):
    subject = forms.CharField(max_length=100)

class PO_Step4(forms.Form):
    subject = forms.CharField(max_length=100)

class PO_Step5(forms.Form):
    subject = forms.CharField(max_length=100)


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
        print "current: %r" % self.steps.current
        return ['po_wizard_step%s.html' % self.steps.current,]
        
    def get_context_data(self, form, **kwargs):
        context = super(PO_Wizard, self).get_context_data(form, **kwargs)
        context.update(wiz_steps=[('1', u'Εισαγωγή στοιχείων Τιμολογίου Εξοπλισμού'), ('2', 'Επιλογή είδους Εξοπλισμού'), ('3', u'Καταχώρηση στοιχείων Εξοπλισμού'), ('4', u'Τελικός έλεγχος'), ('5', u'Επιτυχής καταχώρηση - τέλος') ],
            wiz_width=20)
        return context

def get_po_wizview(*args, **kwargs):
    return PO_Wizard.as_view(**kwargs)

#TemplateView.as_view(template_name="po_wizard_step1.html",
#            extra_context=dict()
#eof
