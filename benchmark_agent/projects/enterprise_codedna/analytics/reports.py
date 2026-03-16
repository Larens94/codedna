# === CODEDNA:0.5 ==============================================
# FILE: analytics/reports.py
# PURPOSE: Reports logic for analytics
# CONTEXT_BUDGET: normal
# DEPENDS_ON: analytics/revenue.py :: monthly_revenue | analytics/cohorts.py :: churn_rate | analytics/usage.py :: get_all_usage
# EXPORTS: full_monthly_report(year, month) -> dict | export_csv(report) -> str
# REQUIRED_BY: api/reports.py | workers/report_generator.py
# DB_TABLES: none
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def full_monthly_report(year: int, month: int):
    rev = monthly_revenue(year, month)
    churn = churn_rate(year, month)
    usage = get_all_usage(month)
    return {'revenue': rev, 'churn_rate': churn, 'usage': usage}
