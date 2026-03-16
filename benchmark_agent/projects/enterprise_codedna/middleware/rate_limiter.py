# === CODEDNA:0.5 ==============================================
# FILE: middleware/rate_limiter.py
# PURPOSE: Rate Limiter logic for middleware
# CONTEXT_BUDGET: minimal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: check_rate_limit() -> bool | get_limit_status() -> dict
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

def check_rate_limit(tenant_id:str, endpoint:str):
    key = f'rate:{tenant_id}:{endpoint}'
    count = cache_get(key) or '0'
    if int(count) > 100: return False
    cache_set(key, str(int(count)+1), ttl=60)
    return True

def get_limit_status(tenant_id:str):
    return {'requests_this_minute': int(cache_get(f'rate:{tenant_id}:global') or '0'), 'limit': 100}
