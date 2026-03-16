"""payments/service.py — Service module.

deps:    payments/invoices.py :: create_invoice | payments/stripe.py :: charge_card | payments/models.py :: mark_paid
exports: collect_payment(invoice_id, payment_method) -> dict | refund_payment(invoice_id, amount_cents) -> dict
used_by: orders/returns.py
tables:  none
rules:   none
"""

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
