"""workers/inventory_sync.py — Inventory Sync module.

deps:    products/inventory.py :: get_stock | core/db.py :: execute
exports: sync_all() -> None | sync_tenant(tenant_id) -> None
used_by: none
tables:  products(id, tenant_id, price_cents, stock_qty, deleted_at)
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def sync_all():
    tenants = execute('SELECT id FROM tenants WHERE suspended_at IS NULL')
    for t in tenants: sync_tenant(t['id'])
