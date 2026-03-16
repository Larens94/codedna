# === CODEDNA:0.5 ==============================================
# FILE: models/session_model.py
# PURPOSE: Session Model logic for models
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: get_session() -> dict|None | list_active_sessions() -> list[dict] | create_session() -> dict | invalidate_session() -> None
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

def get_session(token:str):
    return execute_one('SELECT * FROM sessions WHERE token=%s AND expires_at>NOW()', (token,))

def list_active_sessions(user_id:str):
    return execute('SELECT * FROM sessions WHERE user_id=%s AND expires_at>NOW()', (user_id,))

def create_session(user_id:str, tenant_id:str, token:str):
    return execute_one('INSERT INTO sessions (user_id,tenant_id,token,expires_at) VALUES (%s,%s,%s,NOW()+INTERVAL \'24 hours\') RETURNING *', (user_id,tenant_id,token))

def invalidate_session(token:str):
    execute('UPDATE sessions SET expires_at=NOW() WHERE token=%s', (token,))
