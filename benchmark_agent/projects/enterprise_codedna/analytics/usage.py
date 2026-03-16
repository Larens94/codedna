"""analytics/usage.py — Per-tenant resource usage metrics.

deps:    tenants/models.py :: get_tenant | orders/models.py :: list_orders | products/models.py :: count_products_by_tenant | users/models.py :: count_users_by_tenant
exports: get_tenant_usage(tenant_id) -> dict | get_all_usage(month) -> list[dict]
used_by: analytics/reports.py | api/admin.py
tables:  tenants(id, plan, suspended_at, deleted_at) | orders(id, tenant_id, user_id, items, total_cents, status)
rules:   none
"""

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
