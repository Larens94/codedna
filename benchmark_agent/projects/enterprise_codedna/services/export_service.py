# === CODEDNA:0.5 ==============================================
# FILE: services/export_service.py
# PURPOSE: Export Service logic for services
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: export_invoices_csv() -> str | export_tenants_csv() -> str
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

def export_invoices_csv(year:int, month:int):
    invoices = execute('SELECT * FROM invoices WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))
    return '\n'.join(','.join(str(v) for v in i.values()) for i in invoices)

def export_tenants_csv():
    tenants = execute('SELECT id,name,plan,created_at FROM tenants WHERE deleted_at IS NULL')
    return '\n'.join(','.join(str(v) for v in t.values()) for t in tenants)
