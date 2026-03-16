"""workers/cleanup.py — Cleanup module.

deps:    core/db.py :: execute | core/cache.py :: cache_del
exports: cleanup_expired_carts() -> int | cleanup_old_events() -> int
used_by: none
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def cleanup_expired_carts():
    n = execute('DELETE FROM sessions WHERE expires_at < NOW()')
    return len(n)
