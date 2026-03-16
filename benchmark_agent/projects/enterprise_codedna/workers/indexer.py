"""workers/indexer.py — Indexer module.

deps:    products/models.py :: list_products | tenants/models.py :: list_active_tenants
exports: index_all() -> None | index_tenant(tenant_id) -> None
used_by: none
tables:  products(id, tenant_id, price_cents, stock_qty, deleted_at) | tenants(id, plan, suspended_at, deleted_at)
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def index_tenant(tenant_id: str):
    products = list_products(tenant_id)
    # index each product
