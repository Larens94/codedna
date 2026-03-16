"""products/catalog.py — Catalog module.

deps:    products/models.py :: list_products | core/cache.py :: cache_get | core/cache.py :: cache_set
exports: get_catalog(tenant_id, filters) -> list[dict] | get_product_detail(product_id) -> dict | get_featured(tenant_id) -> list[dict]
used_by: api/products.py
tables:  products(id, tenant_id, price_cents, stock_qty, deleted_at)
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_catalog(tenant_id: str, filters: dict = {}):
    key = f'catalog:{tenant_id}'
    cached = cache_get(key)
    if cached and not filters: return json.loads(cached)
    products = list_products(tenant_id, filters)
    if not filters: cache_set(key, json.dumps(products), ttl=120)
    return products
