# === CODEDNA:0.5 ==============================================
# FILE: orders/checkout.py
# PURPOSE: Cart-to-order conversion with tax calculation
# CONTEXT_BUDGET: normal
# DEPENDS_ON: orders/cart.py :: get_cart | orders/models.py :: create_order | products/pricing.py :: get_price | payments/invoices.py :: create_invoice | core/config.py :: TAX_RATE
# EXPORTS: checkout(session_id, tenant_id, user_id, payment_method) -> dict
# REQUIRED_BY: api/orders.py
# DB_TABLES: orders (id, tenant_id, user_id, items, total_cents, status, created_at) | products (id, tenant_id, name, sku, price_cents, stock_qty, deleted_at)
# AGENT_RULES: applies TAX_RATE exactly once; do NOT apply tax again in payments/invoices.py
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def checkout(session_id: str, tenant_id: str, user_id: str, payment_method: str):
    # @REQUIRES-READ: core/config.py → TAX_RATE — applied exactly once here
    # @MODIFIES-ALSO: payments/invoices.py → create_invoice — receives total already-taxed
    cart = get_cart(session_id)
    if not cart['items']: raise EmptyCartError()
    subtotal = sum(get_price(i['product_id']) * i['qty'] for i in cart['items'])
    tax = round(subtotal * TAX_RATE)
    total = subtotal + tax
    order = create_order(tenant_id, user_id, cart['items'], total)
    invoice = create_invoice(order['id'], tenant_id, total)  # total already includes tax
    return {'order': order, 'invoice': invoice}
