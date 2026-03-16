# === CODEDNA:0.5 ==============================================
# FILE: users/models.py
# PURPOSE: User CRUD; role is string field not boolean flag
# CONTEXT_BUDGET: always
# DEPENDS_ON: core/db.py :: execute | core/db.py :: execute_one
# EXPORTS: get_user(id) -> dict | None | get_user_by_email(email) -> dict | None | create_user(tenant_id, email, name, role) -> dict | update_user(id, data) -> dict | deactivate_user(id) -> None | count_users_by_tenant(tenant_id) -> int
# REQUIRED_BY: tenants/limits.py | users/auth.py | users/service.py
# DB_TABLES: users (id, tenant_id, email, name, role, active, last_login)
# AGENT_RULES: role is STRING ('admin'/'owner'/'member'/'viewer'); no boolean is_admin field exists
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_user(user_id: str):
    return execute_one('SELECT * FROM users WHERE id = %s', (user_id,))

def get_user_by_email(email: str):
    return execute_one('SELECT * FROM users WHERE email = %s AND active = TRUE', (email,))

def create_user(tenant_id: str, email: str, name: str, role: str = 'member'):
    return execute_one('INSERT INTO users (tenant_id, email, name, role) VALUES (%s,%s,%s,%s) RETURNING *', (tenant_id, email, name, role))

def count_users_by_tenant(tenant_id: str):
    row = execute_one('SELECT COUNT(*) as n FROM users WHERE tenant_id = %s AND active = TRUE', (tenant_id,))
    return row['n'] if row else 0
