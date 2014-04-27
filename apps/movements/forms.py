# -*- encoding: utf-8 -*-
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _
from django.utils.html import conditional_escape
from generic_views.forms import DetailForm, InlineModelForm, RModelForm, \
                    ROModelChoiceField, ColumnsDetailWidget, \
                    DetailPlainForeignWidget, UnAutoCompleteField
from ajax_select.fields import AutoCompleteSelectField #, AutoCompleteSelectMultipleField
from inventory.models import Inventory

from django.contrib.auth.models import User
from models import PurchaseRequest, PurchaseRequestItem, PurchaseOrder, \
                   PurchaseOrderItem, Movement, ItemTemplate, RepairOrder
from common.models import Location
from common.api import role_from_request
from assets.models import Item
import datetime

active_locations = Location.objects.filter(active=True)

class UserDetailsWidget(ColumnsDetailWidget):
    show_header = True
    columns = [{ 'name': _('first name'), 'attribute': 'first_name' },
                { 'name': _('last name'), 'attribute': 'last_name' },
                { 'name': _('email'), 'attribute': 'email'},
                # the username is hidden! We don't want to give it away
            ]

class PurchaseRequestForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequest
        exclude = ('active',)


class PurchaseRequestForm_view(DetailForm):
    class Meta:
        model = PurchaseRequest
        exclude = ('active',)


class PurchaseRequestItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequestItem


class PurchaseOrderForm(forms.ModelForm):
    procurement = AutoCompleteSelectField('contracts', label=_("Procurement Contract"),
                show_help_text=False, required=False)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}),
                label=_("Notes"))
    class Meta:
        model = PurchaseOrder
        exclude = ('active', 'validate_user', 'date_val', 'create_user', 
                'purchase_request', 'required_date', 'status' )

    def _pre_save_by_user(self, user):
        if not self.instance.create_user_id:
            self.instance.create_user = user


class PurchaseOrderForm_view(DetailForm):
    class Meta:
        model = PurchaseOrder
        fields = ('user_id', 'procurement', 'issue_date', 'status', 'supplier') # , 'notes') later

def _fmt_movement_items(move):
    return u'<br/>\n\t\t'.join([conditional_escape(unicode(it)) for it in move.items.all()])

class RepairMovesWidget(ColumnsDetailWidget):
    columns = [ {'name': _(u'From'), 'attribute':'location_src' },
            {'name': _(u'To'), 'attribute':'location_dest'},
            {'name': _('Parts'), 'format': _fmt_movement_items },
            ]
    order_by = 'date_act'
    blind_mode = True # we trust the queryset from 'extra_fields' passed to us
    # extra_filter = dict(state='done')

class RepairOrderForm_view(DetailForm):
    create_user = ROModelChoiceField(User.objects.all(),
                widget=UserDetailsWidget, label=_('created by'))
    validate_user = ROModelChoiceField(User.objects.all(),
                widget=UserDetailsWidget, label=_('validated by'))

    class Meta:
        model = RepairOrder
        widgets = {'movements': RepairMovesWidget }

class PurchaseOrderForm_short_view(DetailForm):
    class Meta:
        model = PurchaseOrder
        fields = ('user_id', 'create_user', 'supplier', 'issue_date')

class PurchaseOrderItemForm(forms.ModelForm):
    item_template = AutoCompleteSelectField('product', show_help_text=False, required=False)
    class Meta:
        model = PurchaseOrderItem
        exclude = ('active',)

class PurchaseOrderItemForm_inline(InlineModelForm):
    item_template = AutoCompleteSelectField('product', show_help_text=False, required=False)
    received_qty = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    class Meta:
        verbose_name=_("Order item form")
        model = PurchaseOrderItem
        fields = ('item_name', 'item_template', 'qty', 'received_qty', 'serial_nos')
        # fields left out:  'agreed_price', 'status'

    def clean(self):
        """ hack: fix received_qty, because we have left out the field
        """
        cleaned_data = super(PurchaseOrderItemForm_inline, self).clean()
        if 'qty' in cleaned_data:
            cleaned_data['received_qty'] = cleaned_data['qty']
        item_template = cleaned_data.get('item_template', None)
        if item_template:
            if 'bundled_items' in cleaned_data:
                bundled_items = ItemTemplate.objects.filter(pk__in=cleaned_data['bundled_items']).all()
            else:
                bundled_items = self.instance.bundled_items.all()
            errors = item_template.validate_bundle([(b.category_id, 1) for b in bundled_items])
            if errors:
                self._errors["bundled_items"] = self.error_class(errors)
        return cleaned_data

class PurchaseOrderWizardItemForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(PurchaseOrderWizardItemForm, self).__init__(*args, **kwargs)
        if 'item' in self.initial:
            self.fields['template_id'].initial = self.initial['item'].item_template.id
            self.fields['name'].initial = self.initial['item'].item_template
            self.fields['supplier'].choices = self.initial['item'].item_template.suppliers.all().values_list('id', 'name')
            self.fields['qty'].initial = self.initial['item'].qty

    template_id = forms.CharField(widget=forms.HiddenInput)
    name = forms.CharField(label=_(u'Name'), required=False, widget=forms.TextInput(attrs={'readonly':'readonly'}))
    supplier = forms.ChoiceField(label=_(u'Suppliers'))
    qty = forms.CharField(label=_(u'Qty'))


class PurchaseOrderItemTransferForm(forms.Form):
    purchase_order_item_id = forms.CharField(widget=forms.HiddenInput)
    purchase_order_item = forms.CharField(label=_(u'Purchase order item'), widget=forms.TextInput(attrs={'readonly':'readonly'}))
    inventory = forms.ModelChoiceField(queryset = Inventory.objects.all(), help_text = _(u'Inventory that will receive the item.'))
    qty = forms.CharField(label=_(u'Qty received'))

class SubItemsDetailWidget(ColumnsDetailWidget):
    columns = [{'name': _(u'Item'), 'width': '**'},
            {'name': _('Serial number'), 'attribute': 'serial_number'},
            {'name': _(u'Category'), 'attribute': 'item_template.category.name'},
            {'name': _(u'Manufacturer'), 'attribute': 'item_template.manufacturer.name'},
            ]
    order_by = 'item_template__category__name'

class MovementForm_view(DetailForm):
    location_src = forms.ModelChoiceField(queryset=active_locations,
                widget=DetailPlainForeignWidget, label=_("Source location"))
    location_dest = forms.ModelChoiceField(queryset=active_locations,
                widget=DetailPlainForeignWidget, label=_("Destination location"))

    items = forms.ModelMultipleChoiceField(Item.objects.all(), required=False,
                widget=SubItemsDetailWidget, label=_("Items"))

    create_user = ROModelChoiceField(User.objects.all(),
                widget=UserDetailsWidget, label=_('created by'))
    validate_user = ROModelChoiceField(User.objects.all(),
                widget=UserDetailsWidget, label=_('validated by'))
    src_validate_user = ROModelChoiceField(User.objects.all(),
                widget=UserDetailsWidget, label=_('source validated by'))

    class Meta:
        model = Movement

class _baseMovementForm(RModelForm):
    items = forms.ModelMultipleChoiceField(Item.objects.all(), required=False,
                widget=SubItemsDetailWidget, label=_("Items"),
                help_text=_("You can better select the items by saving this form (using the button below), "
                    "and then picking the items at the next list that will appear."))
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}),
                label=_("Notes"))

    create_user = ROModelChoiceField(User.objects.all(),
                widget=UserDetailsWidget, label=_('created by'))
    validate_user = ROModelChoiceField(User.objects.all(),
                widget=UserDetailsWidget, label=_('validated by'))
    src_validate_user = ROModelChoiceField(User.objects.all(),
                widget=UserDetailsWidget, label=_('source validated by'))


class _outboundMovementForm(_baseMovementForm):
    location_src = AutoCompleteSelectField('location_by_role', label=_("Source location"), required=True, show_help_text=False)

    def _init_by_request(self, request):
        dept = None
        try:
            active_role = role_from_request(request)
            if active_role:
                dept = active_role.department
        except ObjectDoesNotExist:
            pass
        if dept:
            locations = active_locations.filter(department=dept)[:1]
            if locations:
                self.initial['location_src'] = locations[0].id
        UnAutoCompleteField(self.fields, 'location_src', request)
        self.initial['stype'] = 'out'

class MovementForm(_baseMovementForm):
    class Meta:
        model = Movement

class MovementForm_update_po(_baseMovementForm):

    class Meta:
        fields = ('origin', 'note', 'items')
        model = Movement

class MovementForm_gu(_baseMovementForm):
    """ Generic update of a Movement
    """
    location_src = ROModelChoiceField(active_locations, label=_("From") )
    location_dest = ROModelChoiceField(active_locations, label=_("To") )

    checkpoint_src = ROModelChoiceField(Inventory.objects.all(), label=_("Since inventory") )
    checkpoint_dest = ROModelChoiceField(Inventory.objects.all(), label=_("Accounted in inventory") )

    class Meta:
        model = Movement
        exclude = ('name', 'date_val', 'validate_user', 'state', 'stype', 'purchase_order', 'repair_order')

class DestroyItemsForm(_outboundMovementForm):
    """This form is registered whenever defective equipment is trashed (destroyed)
    """
    class Meta:
        model = Movement
        fields = ('date_act', 'origin', 'note', 'location_src', 'items')

    def _pre_save_by_user(self, user):
        self.instance.stype = 'out'
        if not self.instance.create_user_id:
            self.instance.create_user = user
        if not self.instance.location_dest_id:
            name = unicode( _(u'Destroy'))
            self.instance.location_dest= Location.objects.get_or_create(name=name, department=None)[0]

class LoseItemsForm(_outboundMovementForm):
    """ This form is completed whenever equipment is missing (lost/stolen)
    """
    date_act = forms.DateField(label=_(u'date of event'), required=True, initial=datetime.date.today,
                    help_text=_("Format: 23/04/2010"))
    class Meta:
        model = Movement
        fields = ('date_act', 'origin', 'note', 'location_src', 'items')

    def _pre_save_by_user(self, user):
        self.instance.stype = 'out'
        if not self.instance.create_user_id:
            self.instance.create_user = user
        if not self.instance.location_dest_id:
            name = unicode( _(u'Lost'))
            self.instance.location_dest= Location.objects.get_or_create(name=name, department=None)[0]

class MoveItemsForm(_baseMovementForm):
    """ Registered whenever equipment moves from one inventory to another
    """
    location_src = AutoCompleteSelectField('location', label=_("Source location"), required=True, show_help_text=False)
    location_dest = AutoCompleteSelectField('location_by_role', label=_("Destination location"), required=True, show_help_text=False)

    class Meta:
        model = Movement
        fields = ('date_act', 'origin', 'note', 'location_src', 'location_dest',
                'items')

    def _init_by_request(self, request):
        dept = None
        try:
            active_role = role_from_request(request)
            if active_role:
                dept = active_role.department
        except ObjectDoesNotExist:
            pass
        if dept:
            locations = active_locations.filter(department=dept)[:1]
            if locations:
                self.initial['location_dest'] = locations[0].id
        UnAutoCompleteField(self.fields, 'location_dest', request)

    def _pre_save_by_user(self, user):
        self.instance.stype = 'internal'
        if not self.instance.create_user_id:
            self.instance.create_user = user


class MoveInternalForm(_baseMovementForm):
    """ Registered whenever equipment moves from one inventory to another
    """
    location_src = AutoCompleteSelectField('location_by_role', label=_("Source location"), required=True, show_help_text=False)
    location_dest = AutoCompleteSelectField('location_by_role', label=_("Destination location"), required=True, show_help_text=False)

    class Meta:
        model = Movement
        fields = ('date_act', 'origin', 'note', 'location_src', 'location_dest',
                'items')

    def _init_by_request(self, request):
        UnAutoCompleteField(self.fields, 'location_src', request)
        UnAutoCompleteField(self.fields, 'location_dest', request)

    def _pre_save_by_user(self, user):
        self.instance.stype = 'internal'
        if not self.instance.create_user_id:
            self.instance.create_user = user


#eof