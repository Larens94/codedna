# === CODEDNA:0.5 ==============================================
# FILE: api/auth_api.py
# PURPOSE: Auth Api logic for api
# CONTEXT_BUDGET: normal
# DEPENDS_ON: users/auth.py :: login | users/auth.py :: logout | core/auth.py :: verify_token
# EXPORTS: auth_bp (Flask Blueprint)
# REQUIRED_BY: app.py
# DB_TABLES: users (id, tenant_id, email, name, role, active, last_login)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *
from flask import Blueprint, request, jsonify
from core.auth import verify_token, require_auth, require_admin

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def login_route():
    data = request.json
    result = login(data['email'], data['password'])
    return jsonify(result)
