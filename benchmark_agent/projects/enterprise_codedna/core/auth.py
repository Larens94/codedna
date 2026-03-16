# === CODEDNA:0.5 ==============================================
# FILE: core/auth.py
# PURPOSE: JWT sign/verify and role-based access decorators
# CONTEXT_BUDGET: always
# DEPENDS_ON: core/config.py :: JWT_SECRET
# EXPORTS: sign_token(user_id, role, tenant_id) -> str | verify_token(token) -> dict | require_auth (decorator) | require_admin (decorator)
# REQUIRED_BY: users/auth.py | api/products.py | api/orders.py
# DB_TABLES: none
# AGENT_RULES: JWT payload fields: user_id, role, tenant_id. role values: admin/owner/member/viewer
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

import jwt
from functools import wraps

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        try:
            request.user = verify_token(token)
        except Exception:
            return {'error': 'Unauthorized'}, 401
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        try:
            payload = verify_token(token)
            if payload.get('role') != 'admin':
                return {'error': 'Forbidden'}, 403
        except Exception:
            return {'error': 'Unauthorized'}, 401
        return f(*args, **kwargs)
    return decorated

def sign_token(user_id: str, role: str, tenant_id: str):
    return jwt.encode({'user_id': user_id, 'role': role, 'tenant_id': tenant_id}, JWT_SECRET, algorithm='HS256')

def verify_token(token: str):
    return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
