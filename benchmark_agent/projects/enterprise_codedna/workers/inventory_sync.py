# === CODEDNA:0.5 ==============================================
# FILE: workers/inventory_sync.py
# PURPOSE: Inventory Sync logic for workers
# CONTEXT_BUDGET: normal
# DEPENDS_ON: products/inventory.py :: get_stock | core/db.py :: execute
# EXPORTS: sync_all() -> None | sync_tenant(tenant_id) -> None
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

def sync_all():
    tenants = execute('SELECT id FROM tenants WHERE suspended_at IS NULL')
    for t in tenants: sync_tenant(t['id'])
