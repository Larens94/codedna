import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_price(product_id: str, tenant_id: str | None = None):
    product = get_product(product_id)
    return product['price_cents']

def apply_volume_discount(base_price: int, qty: int):
    if qty >= 100: return round(base_price * 0.85)
    if qty >= 50:  return round(base_price * 0.90)
    if qty >= 10:  return round(base_price * 0.95)
    return base_price
