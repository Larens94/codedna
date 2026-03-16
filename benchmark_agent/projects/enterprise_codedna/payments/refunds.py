# === CODEDNA:0.5 ==============================================
# FILE: payments/refunds.py
# PURPOSE: Refunds logic for payments
# CONTEXT_BUDGET: normal
# DEPENDS_ON: payments/stripe.py :: refund_charge | payments/models.py :: get_invoice | orders/models.py :: update_status
# EXPORTS: process_refund(invoice_id, amount_cents) -> dict | full_refund(order_id) -> dict
# REQUIRED_BY: none
# DB_TABLES: orders (id, tenant_id, user_id, items, total_cents, status, created_at)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

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
