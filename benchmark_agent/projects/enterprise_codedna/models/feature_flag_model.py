# === CODEDNA:0.5 ==============================================
# FILE: models/feature_flag_model.py
# PURPOSE: Feature Flag Model logic for models
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: get_flags() -> dict | is_enabled() -> bool | set_flag() -> None
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

def get_flags(tenant_id:str):
    rows = execute('SELECT flag,enabled FROM feature_flags WHERE tenant_id=%s OR tenant_id IS NULL', (tenant_id,))
    return {r['flag']:r['enabled'] for r in rows}

def is_enabled(tenant_id:str, flag:str):
    row = execute_one('SELECT enabled FROM feature_flags WHERE (tenant_id=%s OR tenant_id IS NULL) AND flag=%s ORDER BY tenant_id NULLS LAST LIMIT 1', (tenant_id,flag))
    return row['enabled'] if row else False

def set_flag(tenant_id:str, flag:str, enabled:bool):
    execute('INSERT INTO feature_flags (tenant_id,flag,enabled) VALUES (%s,%s,%s) ON CONFLICT (tenant_id,flag) DO UPDATE SET enabled=%s', (tenant_id,flag,enabled,enabled))
