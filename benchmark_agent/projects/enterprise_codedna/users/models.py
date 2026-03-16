"""users/models.py — User CRUD; role is string, no boolean is_admin field.

deps:    core/db.py :: execute | core/db.py :: execute_one
exports: get_user(id) -> dict | None | get_user_by_email(email) -> dict | None | create_user(tenant_id, email, name, role) -> dict | update_user(id, data) -> dict
used_by: tenants/limits.py | users/auth.py | users/service.py
tables:  users(id, tenant_id, email, role, active)
rules:   role is STRING 'admin' not boolean; check user['role'] == 'admin' never user['is_admin']
"""

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
