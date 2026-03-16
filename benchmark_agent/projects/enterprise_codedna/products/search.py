# === CODEDNA:0.5 ==============================================
# FILE: products/search.py
# PURPOSE: Search logic for products
# CONTEXT_BUDGET: normal
# DEPENDS_ON: products/models.py :: list_products | core/cache.py :: cache_get
# EXPORTS: search(tenant_id, query) -> list[dict] | suggest(tenant_id, prefix) -> list[str]
# REQUIRED_BY: none
# DB_TABLES: products (id, tenant_id, name, sku, price_cents, stock_qty, deleted_at)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def search(tenant_id: str, query: str):
    from core.db import execute
    return execute('SELECT * FROM products WHERE tenant_id = %s AND (name ILIKE %s OR sku ILIKE %s) AND deleted_at IS NULL LIMIT 50', (tenant_id, f'%{query}%', f'%{query}%'))
