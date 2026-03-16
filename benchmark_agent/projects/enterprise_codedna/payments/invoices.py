"""payments/invoices.py — Invoice creation storing pre-taxed total from checkout.

deps:    payments/models.py :: create_invoice_record | core/config.py :: TAX_RATE
exports: create_invoice(order_id, tenant_id, total_cents) -> dict | void_invoice(invoice_id) -> None
used_by: tenants/billing.py | orders/checkout.py | payments/service.py
tables:  none
rules:   total_cents arg is pre-taxed (applied in orders/checkout.py) → do NOT apply TAX_RATE again
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def create_invoice(order_id: str, tenant_id: str, total_cents: int):
    """Persist invoice record; total_cents is already tax-inclusive.

    Depends: orders/checkout.py applies TAX_RATE before calling this.
    Rules:   Do NOT re-apply TAX_RATE. total_cents = subtotal + tax, already computed.
    """
    # total_cents already includes tax from orders/checkout.py  # pre-taxed total from orders/checkout.py — do NOT apply TAX_RATE again
    return create_invoice_record(order_id, tenant_id, total_cents, 'outstanding')  # pre-taxed total from orders/checkout.py — do NOT apply TAX_RATE again
