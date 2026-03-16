# === CODEDNA:0.5 ==============================================
# FILE: workers/cleanup.py
# PURPOSE: Cleanup logic for workers
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute | core/cache.py :: cache_del
# EXPORTS: cleanup_expired_carts() -> int | cleanup_old_events() -> int
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

def cleanup_expired_carts():
    n = execute('DELETE FROM sessions WHERE expires_at < NOW()')
    return len(n)
