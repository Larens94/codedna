# === CODEDNA:0.5 ==============================================
# FILE: analytics/cohorts.py
# PURPOSE: Cohorts logic for analytics
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute | tenants/models.py :: list_active_tenants
# EXPORTS: cohort_retention(months) -> list[dict] | churn_rate(year, month) -> float
# REQUIRED_BY: analytics/reports.py
# DB_TABLES: tenants (id, name, plan, owner_email, suspended_at, deleted_at)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def churn_rate(year: int, month: int):
    total = len(list_active_tenants())
    churned = len(execute('SELECT id FROM tenants WHERE EXTRACT(YEAR FROM deleted_at)=%s AND EXTRACT(MONTH FROM deleted_at)=%s', (year, month)))
    return churned / total if total else 0.0
