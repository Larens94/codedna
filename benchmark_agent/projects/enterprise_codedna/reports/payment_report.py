# === CODEDNA:0.5 ==============================================
# FILE: reports/payment_report.py
# PURPOSE: Payment Report logic for reports
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: get_payments_for_period() -> list[dict] | get_failed_payments() -> list[dict]
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

def get_payments_for_period(year:int, month:int):
    return execute('SELECT * FROM payments WHERE EXTRACT(YEAR FROM paid_at)=%s AND EXTRACT(MONTH FROM paid_at)=%s', (year,month))

def get_failed_payments(days:int=30):
    return execute('SELECT * FROM payments WHERE status=%s AND created_at > NOW()-%s::interval', ('failed',f'{days} days'))
