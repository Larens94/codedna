"""middleware/feature_gate.py — Feature Gate module.

deps:    core/db.py :: execute
exports: gate() -> callable
used_by: none
tables:  none
rules:   none
"""

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
