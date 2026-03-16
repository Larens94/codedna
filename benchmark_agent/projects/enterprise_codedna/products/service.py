# === CODEDNA:0.5 ==============================================
# FILE: products/service.py
# PURPOSE: Service logic for products
# CONTEXT_BUDGET: normal
# DEPENDS_ON: products/models.py | products/inventory.py | tenants/limits.py :: check_product_limit | core/events.py :: emit
# EXPORTS: create(tenant_id, data) -> dict | update(product_id, data) -> dict | delete(product_id) -> None | restock(product_id, qty) -> None
# REQUIRED_BY: api/products.py
# DB_TABLES: products (id, tenant_id, name, sku, price_cents, stock_qty, deleted_at) | tenants (id, name, plan, owner_email, suspended_at, deleted_at)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def create(tenant_id: str, data: dict):
    if not check_product_limit(tenant_id): raise ProductLimitError('Product limit reached')
    product = create_product(tenant_id, data)
    emit('product.updated', {'tenant_id': tenant_id, 'product_id': product['id']})
    return product
