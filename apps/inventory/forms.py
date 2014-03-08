# -*- encoding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext_lazy as _
from ajax_select.fields import AutoCompleteSelectField
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User

from common.api import role_from_request
from common.models import Location
from generic_views.forms import DetailForm, InlineModelForm, \
        ReadOnlyInput, ROModelChoiceField, RModelForm, ReadOnlyDateInput, \
        UnAutoCompleteField

from models import Log, Inventory, InventoryItem
from movements.forms import UserDetailsWidget
import datetime

class LogForm(forms.ModelForm):
    class Meta:
        model = Log


class InventoryForm(RModelForm):
    create_user = ROModelChoiceField(User.objects.all(), label=_("created by"), widget=UserDetailsWidget, required=False)
    location = AutoCompleteSelectField('location_by_role', show_help_text=False, label=_('Location'))
    date_act = forms.DateField(label=_(u'date performed'), initial=datetime.date.today, 
                widget=ReadOnlyDateInput)

    class Meta:
        model = Inventory
        exclude = ('validate_user', 'date_val', 'signed_file', 'state')

    def _pre_save_by_user(self, user):
        if not self.instance.create_user_id:
            self.instance.create_user = user

    def _init_by_request(self, request):
        dept = None
        try:
            active_role = role_from_request(request)
            if active_role:
                dept = active_role.department
        except ObjectDoesNotExist:
            pass
        if dept:
            locations = Location.objects.filter(active=True, department=dept)
            if locations:
                self.initial['location'] = locations[0].id
                self.fields['location'].initial = locations[0].id
        UnAutoCompleteField(self.fields, 'location', request, use_radio=True)

class InventoryValidateForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ('signed_file', 'name')
        widgets = { }


class InventoryForm_view(DetailForm):
    create_user = ROModelChoiceField(User.objects.all(), label=_("created by"), widget=UserDetailsWidget)
    validate_user = ROModelChoiceField(User.objects.all(), label=_("validated by"), widget=UserDetailsWidget)
    class Meta:
        model = Inventory

class InventoryItemForm(forms.ModelForm):
    asset = AutoCompleteSelectField('item', show_help_text=False)
    class Meta:
        model = InventoryItem


class InventoryItemForm_inline(InlineModelForm):
    asset = AutoCompleteSelectField('item', show_help_text=False)
    quantity = forms.fields.IntegerField(required=False, widget=ReadOnlyInput)
    class Meta:
        model = InventoryItem
        exclude = ('notes',)

    def clean(self):
        cleaned_data = super(InventoryItemForm_inline, self).clean()
        cleaned_data['quantity'] = 1
        return cleaned_data

#eof
