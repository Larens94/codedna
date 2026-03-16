# === CODEDNA:0.5 ==============================================
# FILE: analytics/revenue.py
# PURPOSE: Monthly/annual revenue totals from paid invoices
# CONTEXT_BUDGET: normal
# DEPENDS_ON: payments/models.py :: get_invoices_for_period | tenants/models.py :: is_suspended
# EXPORTS: monthly_revenue(year, month) -> dict | annual_summary(year) -> list[dict] | revenue_by_tenant(year, month) -> dict
# REQUIRED_BY: analytics/reports.py | notifications/scheduler.py
# DB_TABLES: tenants (id, name, plan, owner_email, suspended_at, deleted_at)
# AGENT_RULES: MUST filter is_suspended() before summing; see tenants/models.py → is_suspended()
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def monthly_revenue(year: int, month: int):
    # @REQUIRES-READ: payments/models.py → get_invoices_for_period — returns all invoices; NO suspended filter
    # @REQUIRES-READ: tenants/models.py → is_suspended — use to exclude suspended tenants
    # @SEE: tenants/models.py → list_active_tenants — reference for correct suspension check
    invoices = get_invoices_for_period(year, month)
    total = sum(i['amount_cents'] for i in invoices)
    by_tenant = {}
    for i in invoices:
        by_tenant.setdefault(i['tenant_id'], []).append(i)
    return {'year': year, 'month': month, 'total_cents': total, 'by_tenant': by_tenant}
