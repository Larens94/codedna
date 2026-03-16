"""middleware/rate_limiter.py — Rate Limiter module.

deps:    core/db.py :: execute
exports: check_rate_limit() -> bool | get_limit_status() -> dict
used_by: none
tables:  none
rules:   none
"""

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
