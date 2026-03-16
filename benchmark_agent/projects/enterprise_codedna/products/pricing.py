"""products/pricing.py — Pricing module.

deps:    products/models.py :: get_product | tenants/models.py :: get_tenant
exports: get_price(product_id, tenant_id) -> int | apply_volume_discount(base_price, qty) -> int | get_price_with_tax(product_id) -> int
used_by: orders/checkout.py
tables:  products(id, tenant_id, price_cents, stock_qty, deleted_at) | tenants(id, plan, suspended_at, deleted_at)
rules:   none
"""

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
