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
