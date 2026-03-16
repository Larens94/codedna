# === CODEDNA:0.5 ==============================================
# FILE: middleware/cors_handler.py
# PURPOSE: Cors Handler logic for middleware
# CONTEXT_BUDGET: minimal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: add_cors_headers() -> object
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

def add_cors_headers(response:object):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response
