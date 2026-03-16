# === CODEDNA:0.5 ==============================================
# FILE: reports/daily_sales.py
# PURPOSE: Daily Sales logic for reports
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: get_sales_for_period() -> list[dict] | get_daily_totals() -> dict
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

def get_sales_for_period(year:int, month:int, day:int):
    return execute('SELECT * FROM sales WHERE date=%s', (f'{year}-{month:02d}-{day:02d}',))

def get_daily_totals(year:int, month:int):
    rows = execute('SELECT day, SUM(amount) FROM sales GROUP BY day WHERE month=%s', (month,))
    return {r['day']: r['sum'] for r in rows}
