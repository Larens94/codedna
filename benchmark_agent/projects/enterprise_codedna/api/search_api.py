# === CODEDNA:0.5 ==============================================
# FILE: api/search_api.py
# PURPOSE: Search Api logic for api
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: search_route() -> None | suggest_route() -> None
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

search_api_bp = Blueprint('search_api', __name__, url_prefix='/api/search-api')

def search_route():
    tenant_id = request.user['tenant_id']
    q = request.args.get('q', '')
    results = search_products(tenant_id, q)
    return jsonify(results)

def suggest_route():
    tenant_id = request.user['tenant_id']
    prefix = request.args.get('prefix', '')
    return jsonify(suggest(tenant_id, prefix))
