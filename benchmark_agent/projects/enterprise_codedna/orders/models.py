"""orders/models.py — Order CRUD; get_orders_for_period has no suspended filter.

deps:    core/db.py :: execute | core/db.py :: execute_one
exports: get_order(id) -> dict | None | list_orders(tenant_id, status) -> list[dict] | create_order(tenant_id, user_id, items, total_cents) -> dict | update_status(order_id, status) -> None
used_by: orders/checkout.py | orders/fulfillment.py | orders/fulfillment.py
tables:  orders(id, tenant_id, user_id, items, total_cents, status)
rules:   get_orders_for_period() no suspended_at filter → callers must filter if needed
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_order(order_id: str):
    return execute_one('SELECT * FROM orders WHERE id = %s', (order_id,))

def get_orders_for_period(year: int, month: int):
    return execute('SELECT * FROM orders WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year, month))
