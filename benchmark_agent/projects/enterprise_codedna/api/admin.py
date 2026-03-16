# === CODEDNA:0.5 ==============================================
# FILE: api/admin.py
# PURPOSE: Admin logic for api
# CONTEXT_BUDGET: normal
# DEPENDS_ON: tenants/service.py :: suspend | tenants/service.py :: reactivate | analytics/usage.py :: get_tenant_usage | core/auth.py :: require_admin
# EXPORTS: admin_bp (Flask Blueprint)
# REQUIRED_BY: app.py
# DB_TABLES: tenants (id, name, plan, owner_email, suspended_at, deleted_at)
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

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

def suspend_tenant_route():
    tid = request.view_args['tenant_id']
    reason = request.json.get('reason', '')
    suspend(tid, reason)
    return jsonify({'status': 'suspended'})
