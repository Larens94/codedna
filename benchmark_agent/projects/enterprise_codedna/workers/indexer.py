# === CODEDNA:0.5 ==============================================
# FILE: workers/indexer.py
# PURPOSE: Indexer logic for workers
# CONTEXT_BUDGET: normal
# DEPENDS_ON: products/models.py :: list_products | tenants/models.py :: list_active_tenants
# EXPORTS: index_all() -> None | index_tenant(tenant_id) -> None
# REQUIRED_BY: none
# DB_TABLES: products (id, tenant_id, name, sku, price_cents, stock_qty, deleted_at) | tenants (id, name, plan, owner_email, suspended_at, deleted_at)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def index_tenant(tenant_id: str):
    products = list_products(tenant_id)
    # index each product
