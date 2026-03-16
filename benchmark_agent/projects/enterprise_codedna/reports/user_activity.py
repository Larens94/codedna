# === CODEDNA:0.5 ==============================================
# FILE: reports/user_activity.py
# PURPOSE: User Activity logic for reports
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: get_active_users() -> list[dict] | get_user_sessions_for_period() -> list[dict]
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

def get_active_users(tenant_id:str, days:int=30):
    return execute('SELECT * FROM users WHERE tenant_id=%s AND last_login > NOW() - %s::interval AND deleted_at IS NULL', (tenant_id, f'{days} days'))

def get_user_sessions_for_period(year:int, month:int):
    return execute('SELECT * FROM sessions WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))
