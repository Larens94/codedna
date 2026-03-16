"""middleware/tenant_resolver.py — Tenant Resolver module.

deps:    core/db.py :: execute
exports: resolve_tenant() -> dict|None | inject_tenant_context() -> callable
used_by: none
tables:  none
rules:   none
"""

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
