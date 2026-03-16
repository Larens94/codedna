# === CODEDNA:0.5 ==============================================
# FILE: tenants/billing.py
# PURPOSE: Billing logic for tenants
# CONTEXT_BUDGET: normal
# DEPENDS_ON: tenants/models.py :: list_active_tenants | subscriptions/models.py :: get_by_tenant | payments/invoices.py :: create_invoice
# EXPORTS: bill_all_tenants(year, month) -> list[dict] | bill_tenant(tenant_id, year, month) -> dict
# REQUIRED_BY: workers/billing_runner.py
# DB_TABLES: tenants (id, name, plan, owner_email, suspended_at, deleted_at) | subscriptions (id, tenant_id, plan, status, next_billing_at)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

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
