import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def collect_payment(invoice_id: str, payment_method: str):
    invoice = get_invoice(invoice_id)
    if invoice['status'] != 'outstanding': raise ValueError('Not collectable')
    charge = charge_card(invoice['amount_cents'], payment_method)
    mark_paid(invoice_id, charge['id'])
    return charge
