# === CODEDNA:0.5 ==============================================
# FILE: users/auth.py
# PURPOSE: Auth logic for users
# CONTEXT_BUDGET: normal
# DEPENDS_ON: users/models.py :: get_user_by_email | core/auth.py :: sign_token | core/cache.py :: cache_set
# EXPORTS: login(email, password) -> dict | logout(token) -> None | refresh(token) -> str
# REQUIRED_BY: api/auth_api.py | api/auth_api.py
# DB_TABLES: users (id, tenant_id, email, name, role, active, last_login)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def login(email: str, password: str):
    user = get_user_by_email(email)
    if not user or not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        raise ValueError('Invalid credentials')
    token = sign_token(user['id'], user['role'], user['tenant_id'])
    return {'token': token, 'user': user}
