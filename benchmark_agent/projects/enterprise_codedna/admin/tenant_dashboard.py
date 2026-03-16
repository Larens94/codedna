# === CODEDNA:0.5 ==============================================
# FILE: admin/tenant_dashboard.py
# PURPOSE: Tenant Dashboard logic for admin
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: get_overview() -> dict | get_tenants_for_period() -> list[dict]
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

def get_overview():
    total = execute_one('SELECT COUNT(*) as n FROM tenants WHERE deleted_at IS NULL')
    suspended = execute_one('SELECT COUNT(*) as n FROM tenants WHERE suspended_at IS NOT NULL AND deleted_at IS NULL')
    return {'total':total['n'],'suspended':suspended['n'],'active':total['n']-suspended['n']}

def get_tenants_for_period(year:int, month:int):
    return execute('SELECT * FROM tenants WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))
