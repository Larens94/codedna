# === CODEDNA:0.5 ==============================================
# FILE: workers/analytics_aggregator.py
# PURPOSE: Analytics Aggregator logic for workers
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: aggregate_daily_revenue() -> dict | aggregate_monthly_cohorts() -> None
# REQUIRED_BY: none
# DB_TABLES: none
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def aggregate_daily_revenue(date:str):
    rows = execute('SELECT tenant_id, SUM(amount_cents) as total FROM invoices WHERE DATE(created_at)=%s GROUP BY tenant_id', (date,))
    return {r['tenant_id']: r['total'] for r in rows}

def aggregate_monthly_cohorts(year:int, month:int):
    execute('INSERT INTO cohort_snapshots (year,month,metrics) SELECT %s,%s,json_build_object() ON CONFLICT DO NOTHING', (year,month))
