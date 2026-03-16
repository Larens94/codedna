"""analytics/reports.py — Reports module.

deps:    analytics/revenue.py :: monthly_revenue | analytics/cohorts.py :: churn_rate | analytics/usage.py :: get_all_usage
exports: full_monthly_report(year, month) -> dict | export_csv(report) -> str
used_by: api/reports.py | workers/report_generator.py
tables:  none
rules:   none
"""

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
