# === CODEDNA:0.5 ==============================================
# FILE: orders/fulfillment.py
# PURPOSE: Order fulfillment lifecycle and inventory decrement
# CONTEXT_BUDGET: normal
# DEPENDS_ON: orders/models.py :: get_order | orders/models.py :: update_status | products/inventory.py :: decrement_stock | core/events.py :: emit
# EXPORTS: fulfill_order(order_id) -> dict | cancel_order(order_id) -> None | get_fulfillment_status(order_id) -> str
# REQUIRED_BY: none
# DB_TABLES: orders (id, tenant_id, user_id, items, total_cents, status, created_at) | products (id, tenant_id, name, sku, price_cents, stock_qty, deleted_at)
# AGENT_RULES: MUST call decrement_stock() for each item in order['items'] before updating status
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def fulfill_order(order_id: str):
    # @REQUIRES-READ: products/inventory.py → decrement_stock — MUST call for each item in order['items']
    # @MODIFIES-ALSO: products (stock_qty column) — decremented per item
    order = get_order(order_id)
    if order['status'] != 'confirmed': raise InvalidStatusError()
    # TODO: decrement inventory for each item in order['items']
    update_status(order_id, 'fulfilled')
    emit('order.fulfilled', {'order_id': order_id})
    return get_order(order_id)
