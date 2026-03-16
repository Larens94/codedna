"""analytics/cohorts.py — Cohorts module.

deps:    core/db.py :: execute | tenants/models.py :: list_active_tenants
exports: cohort_retention(months) -> list[dict] | churn_rate(year, month) -> float
used_by: analytics/reports.py
tables:  tenants(id, plan, suspended_at, deleted_at)
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def churn_rate(year: int, month: int):
    total = len(list_active_tenants())
    churned = len(execute('SELECT id FROM tenants WHERE EXTRACT(YEAR FROM deleted_at)=%s AND EXTRACT(MONTH FROM deleted_at)=%s', (year, month)))
    return churned / total if total else 0.0
