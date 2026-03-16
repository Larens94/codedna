"""products/service.py — Service module.

deps:    products/models.py | products/inventory.py | tenants/limits.py :: check_product_limit | core/events.py :: emit
exports: create(tenant_id, data) -> dict | update(product_id, data) -> dict | delete(product_id) -> None | restock(product_id, qty) -> None
used_by: api/products.py
tables:  products(id, tenant_id, price_cents, stock_qty, deleted_at) | tenants(id, plan, suspended_at, deleted_at)
rules:   none
"""

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
