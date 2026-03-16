"""users/auth.py — Auth module.

deps:    users/models.py :: get_user_by_email | core/auth.py :: sign_token | core/cache.py :: cache_set
exports: login(email, password) -> dict | logout(token) -> None | refresh(token) -> str
used_by: api/auth_api.py | api/auth_api.py
tables:  users(id, tenant_id, email, role, active)
rules:   none
"""

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
