"""products/inventory.py — Stock quantity read/write with low-stock detection.

deps:    core/db.py :: execute | core/db.py :: execute_one | core/config.py :: LOW_STOCK_THRESHOLD
exports: get_stock(product_id) -> int | check_stock(product_id, qty) -> bool | decrement_stock(product_id, qty) -> None | increment_stock(product_id, qty) -> None
used_by: products/service.py | orders/cart.py | orders/fulfillment.py
tables:  products(id, tenant_id, price_cents, stock_qty, deleted_at)
rules:   check_stock + decrement_stock are NOT atomic → use single UPDATE for concurrency; T3: after decrement call send_low_stock_alert() if is_low_stock()
"""

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
    """Decrement stock for a product by qty.

    Depends: called by orders/fulfillment.py after order confirmed.
    Rules:   Not atomic with check_stock(); high-concurrency callers use single UPDATE.
             T3: call send_low_stock_alert() if is_low_stock() after decrement.
    """
    execute('UPDATE products SET stock_qty = stock_qty - %s WHERE id = %s', (qty, product_id))

def is_low_stock(product_id: str):
    return get_stock(product_id) < LOW_STOCK_THRESHOLD
