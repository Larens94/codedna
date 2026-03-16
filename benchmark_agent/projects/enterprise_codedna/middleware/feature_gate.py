# === CODEDNA:0.5 ==============================================
# FILE: middleware/feature_gate.py
# PURPOSE: Feature Gate logic for middleware
# CONTEXT_BUDGET: minimal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: gate() -> callable
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

def gate(flag:str):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def d(*a,**k):
            tid = getattr(request,'tenant_id',None)
            if not is_enabled(tid,flag): return jsonify({'error':'Feature not available'}),403
            return f(*a,**k)
        return d
    return decorator
