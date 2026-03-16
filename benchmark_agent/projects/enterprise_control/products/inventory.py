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
    execute('UPDATE products SET stock_qty = stock_qty - %s WHERE id = %s', (qty, product_id))

def is_low_stock(product_id: str):
    return get_stock(product_id) < LOW_STOCK_THRESHOLD
