"""analytics/revenue.py — Monthly/annual revenue aggregation from paid invoices.

deps:    payments/models.py :: get_invoices_for_period | tenants/models.py :: is_suspended
exports: monthly_revenue(year, month) -> dict | annual_summary(year) -> list[dict] | revenue_by_tenant(year, month) -> dict
used_by: analytics/reports.py | notifications/scheduler.py
tables:  tenants(id, plan, suspended_at, deleted_at)
rules:   get_invoices_for_period() returns ALL tenants no suspended filter → MUST call is_suspended() BEFORE summing
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def monthly_revenue(year: int, month: int):
    """Aggregate paid invoices into monthly revenue total.

    Depends: payments.models.get_invoices_for_period — returns ALL invoices, NO suspended filter.
    Rules:   MUST filter is_suspended() from tenants.models BEFORE summing.
    """
    invoices = get_invoices_for_period(year, month)  # includes suspended tenants — filter with is_suspended() before aggregating
    total = sum(i['amount_cents'] for i in invoices)  # BUG ZONE: suspended tenant invoices included in total
    by_tenant = {}
    for i in invoices:
        by_tenant.setdefault(i['tenant_id'], []).append(i)
    return {'year': year, 'month': month, 'total_cents': total, 'by_tenant': by_tenant}
