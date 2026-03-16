# === CODEDNA:0.5 ==============================================
# FILE: admin/billing_dashboard.py
# PURPOSE: Billing Dashboard logic for admin
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: get_billing_summary() -> dict | get_failed_billing() -> list[dict]
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

def get_billing_summary(year:int, month:int):
    invoices = execute('SELECT SUM(amount_cents) as total, COUNT(*) as count FROM invoices WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))
    return invoices[0] if invoices else {}

def get_failed_billing():
    return execute('SELECT * FROM invoices WHERE status=%s ORDER BY created_at DESC LIMIT 50', ('failed',))
