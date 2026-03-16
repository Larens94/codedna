"""orders/checkout.py — Cart-to-order conversion with single-pass tax calculation.

deps:    orders/cart.py :: get_cart | orders/models.py :: create_order | products/pricing.py :: get_price | payments/invoices.py :: create_invoice | core/config.py :: TAX_RATE
exports: checkout(session_id, tenant_id, user_id, payment_method) -> dict
used_by: api/orders.py
tables:  orders(id, tenant_id, user_id, items, total_cents, status) | products(id, tenant_id, price_cents, stock_qty, deleted_at)
rules:   applies TAX_RATE exactly once here → do NOT re-apply in payments/invoices.py
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def checkout(session_id: str, tenant_id: str, user_id: str, payment_method: str):
    """Convert cart to confirmed order, apply tax once, create invoice.

    Rules:   TAX_RATE applied exactly once here: total = subtotal + round(subtotal * TAX_RATE).
             payments/invoices.py receives pre-taxed total — must NOT re-apply tax.
    """
    cart = get_cart(session_id)
    if not cart['items']: raise EmptyCartError()
    subtotal = sum(get_price(i['product_id']) * i['qty'] for i in cart['items'])
    tax = round(subtotal * TAX_RATE)  # tax applied exactly once here — do NOT re-apply in payments/invoices.py
    total = subtotal + tax
    order = create_order(tenant_id, user_id, cart['items'], total)
    invoice = create_invoice(order['id'], tenant_id, total)  # total already includes tax
    return {'order': order, 'invoice': invoice}
