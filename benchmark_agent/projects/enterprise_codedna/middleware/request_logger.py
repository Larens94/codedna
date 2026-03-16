# === CODEDNA:0.5 ==============================================
# FILE: middleware/request_logger.py
# PURPOSE: Request Logger logic for middleware
# CONTEXT_BUDGET: minimal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: log_request() -> None | get_slow_requests() -> list[dict]
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

def log_request(request:object, response:object, duration_ms:float):
    execute('INSERT INTO request_logs (method,path,status,duration_ms,tenant_id) VALUES (%s,%s,%s,%s,%s)', (request.method, request.path, response.status_code, duration_ms, getattr(request,'tenant_id',None)))

def get_slow_requests(threshold_ms:float=1000):
    return execute('SELECT * FROM request_logs WHERE duration_ms > %s ORDER BY duration_ms DESC LIMIT 50', (threshold_ms,))
