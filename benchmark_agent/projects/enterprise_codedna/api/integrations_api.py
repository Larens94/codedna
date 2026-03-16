# === CODEDNA:0.5 ==============================================
# FILE: api/integrations_api.py
# PURPOSE: Integrations Api logic for api
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: list_integrations_route() -> None | create_integration_route() -> None
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
from flask import Blueprint, request, jsonify
from core.auth import verify_token, require_auth, require_admin

integrations_api_bp = Blueprint('integrations_api', __name__, url_prefix='/api/integrations-api')

def list_integrations_route():
    tenant_id = request.user['tenant_id']
    return jsonify(get_integrations(tenant_id))

def create_integration_route():
    data = request.json
    tenant_id = request.user['tenant_id']
    result = create_integration(tenant_id, data['provider'], data['config'])
    return jsonify(result),201
