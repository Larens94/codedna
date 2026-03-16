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
