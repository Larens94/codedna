# === CODEDNA:0.5 ==============================================
# FILE: middleware/tenant_resolver.py
# PURPOSE: Tenant Resolver logic for middleware
# CONTEXT_BUDGET: minimal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: resolve_tenant() -> dict|None | inject_tenant_context() -> callable
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

def resolve_tenant(request:object):
    host = request.host
    return execute_one('SELECT * FROM tenants WHERE custom_domain=%s AND suspended_at IS NULL AND deleted_at IS NULL', (host,))

def inject_tenant_context(f:callable):
    from functools import wraps
    @wraps(f)
    def decorated(*args,**kwargs): return f(*args,**kwargs)
    return decorated
