# === CODEDNA:0.5 ==============================================
# FILE: orders/models.py
# PURPOSE: Models logic for orders
# CONTEXT_BUDGET: always
# DEPENDS_ON: core/db.py :: execute | core/db.py :: execute_one
# EXPORTS: get_order(id) -> dict | None | list_orders(tenant_id, status) -> list[dict] | create_order(tenant_id, user_id, items, total_cents) -> dict | update_status(order_id, status) -> None | get_orders_for_period(year, month) -> list[dict]
# REQUIRED_BY: orders/checkout.py | orders/fulfillment.py | orders/fulfillment.py
# DB_TABLES: orders (id, tenant_id, user_id, items, total_cents, status, created_at)
# AGENT_RULES: get_orders_for_period does NOT filter suspended tenants
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_order(order_id: str):
    return execute_one('SELECT * FROM orders WHERE id = %s', (order_id,))

def get_orders_for_period(year: int, month: int):
    return execute('SELECT * FROM orders WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year, month))
