# === CODEDNA:0.5 ==============================================
# FILE: products/pricing.py
# PURPOSE: Pricing logic for products
# CONTEXT_BUDGET: normal
# DEPENDS_ON: products/models.py :: get_product | tenants/models.py :: get_tenant
# EXPORTS: get_price(product_id, tenant_id) -> int | apply_volume_discount(base_price, qty) -> int | get_price_with_tax(product_id) -> int
# REQUIRED_BY: orders/checkout.py
# DB_TABLES: products (id, tenant_id, name, sku, price_cents, stock_qty, deleted_at) | tenants (id, name, plan, owner_email, suspended_at, deleted_at)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

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
