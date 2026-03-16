# === CODEDNA:0.5 ==============================================
# FILE: admin/support_tools.py
# PURPOSE: Support Tools logic for admin
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: impersonate_tenant() -> str | reset_tenant_cache() -> None | get_system_health() -> dict
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

def impersonate_tenant(admin_user_id:str, target_tenant_id:str):
    from core.auth import sign_token
    return sign_token(admin_user_id,'admin',target_tenant_id)

def reset_tenant_cache(tenant_id:str):
    from core.cache import cache_invalidate_prefix
    cache_invalidate_prefix(f'tenant:{tenant_id}')
    cache_invalidate_prefix(f'catalog:{tenant_id}')

def get_system_health():
    return {'db': 'ok', 'redis': 'ok', 'stripe': 'ok'}
