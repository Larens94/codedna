# === CODEDNA:0.5 ==============================================
# FILE: models/audit_model.py
# PURPOSE: Audit Model logic for models
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: get_audit_entries() -> list[dict] | get_audit_for_period() -> list[dict]
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

def get_audit_entries(resource_id:str):
    return execute('SELECT * FROM audit_log WHERE resource_id=%s ORDER BY created_at DESC', (resource_id,))

def get_audit_for_period(year:int, month:int):
    return execute('SELECT * FROM audit_log WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))
