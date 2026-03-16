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
