# === CODEDNA:0.5 ==============================================
# FILE: analytics/usage.py
# PURPOSE: Per-tenant resource usage metrics for admin dashboard
# CONTEXT_BUDGET: normal
# DEPENDS_ON: tenants/models.py :: get_tenant | orders/models.py :: list_orders | products/models.py :: count_products_by_tenant | users/models.py :: count_users_by_tenant
# EXPORTS: get_tenant_usage(tenant_id) -> dict | get_all_usage(month) -> list[dict]
# REQUIRED_BY: analytics/reports.py | api/admin.py
# DB_TABLES: tenants (id, name, plan, owner_email, suspended_at, deleted_at) | orders (id, tenant_id, user_id, items, total_cents, status, created_at)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_tenant_usage(tenant_id: str):
    orders = list_orders(tenant_id, status=None)
    return {
        'tenant_id': tenant_id,
        'order_count': len(orders),
        'product_count': count_products_by_tenant(tenant_id),
        'user_count': count_users_by_tenant(tenant_id),
    }
