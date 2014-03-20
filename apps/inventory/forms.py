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

from models import Log, InventoryGroup, InventoryItem
from movements.forms import UserDetailsWidget
import datetime

class LogForm(forms.ModelForm):
    class Meta:
        model = Log


class InventoryForm(RModelForm):
    create_user = ROModelChoiceField(User.objects.all(), label=_("created by"), widget=UserDetailsWidget, required=False)
    department = AutoCompleteSelectField('department', label=_("Department"), show_help_text=False)
    date_act = forms.DateField(label=_(u'date performed'), initial=datetime.date.today, 
                widget=ReadOnlyDateInput)

    class Meta:
        model = InventoryGroup
        exclude = ('validate_user', 'date_val', 'signed_file', 'state')

    def _pre_save_by_user(self, user):
        if not self.instance.create_user_id:
            self.instance.create_user = user

    def _init_by_request(self, request):
        try:
            active_role = role_from_request(request)
            if active_role:
                self.initial['department'] = active_role.department.id
                self.fields['department'].initial = active_role.department.id
        except ObjectDoesNotExist:
            pass
        UnAutoCompleteField(self.fields, 'department', request, use_radio=False)

class InventoryValidateForm(forms.ModelForm):
    class Meta:
        model = InventoryGroup
        fields = ('signed_file', 'name')
        widgets = { }


class InventoryForm_view(DetailForm):
    create_user = ROModelChoiceField(User.objects.all(), label=_("created by"), widget=UserDetailsWidget)
    validate_user = ROModelChoiceField(User.objects.all(), label=_("validated by"), widget=UserDetailsWidget)
    class Meta:
        model = InventoryGroup

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
