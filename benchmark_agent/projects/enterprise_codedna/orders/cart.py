# === CODEDNA:0.5 ==============================================
# FILE: orders/cart.py
# PURPOSE: Redis-backed cart with stock check on item add
# CONTEXT_BUDGET: normal
# DEPENDS_ON: products/models.py :: get_product | products/inventory.py :: check_stock | core/cache.py :: cache_get | core/cache.py :: cache_set
# EXPORTS: add_item(session_id, product_id, qty) -> dict | remove_item(session_id, product_id) -> None | get_cart(session_id) -> dict | clear_cart(session_id) -> None
# REQUIRED_BY: orders/checkout.py
# DB_TABLES: orders (id, tenant_id, user_id, items, total_cents, status, created_at) | products (id, tenant_id, name, sku, price_cents, stock_qty, deleted_at)
# AGENT_RULES: T1: discount_code field must be stored in cart dict for checkout to apply
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_cart(session_id: str):
    raw = cache_get(f'cart:{session_id}')
    return json.loads(raw) if raw else {'items': [], 'session_id': session_id}

def add_item(session_id: str, product_id: str, qty: int):
    if not check_stock(product_id, qty): raise OutOfStockError(product_id)
    cart = get_cart(session_id)
    existing = next((i for i in cart['items'] if i['product_id'] == product_id), None)
    if existing: existing['qty'] += qty
    else: cart['items'].append({'product_id': product_id, 'qty': qty})
    cache_set(f'cart:{session_id}', json.dumps(cart), ttl=3600)
    return cart
