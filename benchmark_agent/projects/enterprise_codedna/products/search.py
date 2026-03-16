"""products/search.py — Search module.

deps:    products/models.py :: list_products | core/cache.py :: cache_get
exports: search(tenant_id, query) -> list[dict] | suggest(tenant_id, prefix) -> list[str]
used_by: none
tables:  products(id, tenant_id, price_cents, stock_qty, deleted_at)
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def search(tenant_id: str, query: str):
    from core.db import execute
    return execute('SELECT * FROM products WHERE tenant_id = %s AND (name ILIKE %s OR sku ILIKE %s) AND deleted_at IS NULL LIMIT 50', (tenant_id, f'%{query}%', f'%{query}%'))
