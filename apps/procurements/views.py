# -*- encoding: utf-8 -*-
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from models import Contract

def contract_get_description(request, pk):
    """
    Take a purchase order and call transfer_to_inventory to transfer and
    close all of its item and close the purchase order too
    """
    contract = get_object_or_404(Contract, pk=pk)
    return HttpResponse(contract.description or '', content_type='text/plain')

#eof
