# === CODEDNA:0.5 ==============================================
# FILE: products/inventory.py
# PURPOSE: Stock quantity read/write with low-stock detection
# CONTEXT_BUDGET: always
# DEPENDS_ON: core/db.py :: execute | core/db.py :: execute_one | core/config.py :: LOW_STOCK_THRESHOLD
# EXPORTS: get_stock(product_id) -> int | check_stock(product_id, qty) -> bool | decrement_stock(product_id, qty) -> None | increment_stock(product_id, qty) -> None | is_low_stock(product_id) -> bool
# REQUIRED_BY: products/service.py | orders/cart.py | orders/fulfillment.py
# DB_TABLES: products (id, tenant_id, name, sku, price_cents, stock_qty, deleted_at)
# AGENT_RULES: check_stock + decrement_stock are NOT atomic; use single UPDATE for concurrency safety
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_stock(product_id: str):
    row = execute_one('SELECT stock_qty FROM products WHERE id = %s', (product_id,))
    return row['stock_qty'] if row else 0

def check_stock(product_id: str, qty: int):
    return get_stock(product_id) >= qty

def decrement_stock(product_id: str, qty: int):
    # @SEE: orders/fulfillment.py → fulfill_order — this is where decrement SHOULD be called
    execute('UPDATE products SET stock_qty = stock_qty - %s WHERE id = %s', (qty, product_id))

def is_low_stock(product_id: str):
    return get_stock(product_id) < LOW_STOCK_THRESHOLD
