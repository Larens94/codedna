# === CODEDNA:0.5 ==============================================
# FILE: orders/returns.py
# PURPOSE: Returns logic for orders
# CONTEXT_BUDGET: normal
# DEPENDS_ON: orders/models.py :: get_order | products/inventory.py :: increment_stock | payments/service.py :: refund_payment
# EXPORTS: initiate_return(order_id, items, reason) -> dict | approve_return(return_id) -> None | get_return(return_id) -> dict
# REQUIRED_BY: none
# DB_TABLES: orders (id, tenant_id, user_id, items, total_cents, status, created_at) | products (id, tenant_id, name, sku, price_cents, stock_qty, deleted_at)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def initiate_return(order_id: str, items: list, reason: str):
    order = get_order(order_id)
    if order['status'] != 'fulfilled': raise InvalidStatusError()
    return execute_one('INSERT INTO returns (order_id, items, reason, status) VALUES (%s,%s,%s,%s) RETURNING *', (order_id, json.dumps(items), reason, 'pending'))
