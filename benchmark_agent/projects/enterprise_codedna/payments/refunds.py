"""payments/refunds.py — Refunds module.

deps:    payments/stripe.py :: refund_charge | payments/models.py :: get_invoice | orders/models.py :: update_status
exports: process_refund(invoice_id, amount_cents) -> dict | full_refund(order_id) -> dict
used_by: none
tables:  orders(id, tenant_id, user_id, items, total_cents, status)
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def full_refund(order_id: str):
    from orders.models import get_order
    order = get_order(order_id)
    invoice = get_invoice(order['invoice_id'])
    refund = refund_charge(invoice['stripe_charge_id'], invoice['amount_cents'])
    update_status(order_id, 'returned')
    return refund
