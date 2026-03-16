"""tenants/billing.py — Billing module.

deps:    tenants/models.py :: list_active_tenants | subscriptions/models.py :: get_by_tenant | payments/invoices.py :: create_invoice
exports: bill_all_tenants(year, month) -> list[dict] | bill_tenant(tenant_id, year, month) -> dict
used_by: workers/billing_runner.py
tables:  tenants(id, plan, suspended_at, deleted_at) | subscriptions(id, tenant_id, plan, status, next_billing_at)
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def bill_all_tenants(year: int, month: int):
    tenants = list_active_tenants()
    results = []
    for t in tenants:
        try: results.append(bill_tenant(t['id'], year, month))
        except Exception as e: log(f'Billing failed for {t["id"]}: {e}')
    return results
