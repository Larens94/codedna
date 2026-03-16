# === CODEDNA:0.5 ==============================================
# FILE: api/products.py
# PURPOSE: CRUD endpoints for products scoped by tenant
# CONTEXT_BUDGET: normal
# DEPENDS_ON: products/service.py | products/catalog.py | core/auth.py :: require_auth | users/permissions.py :: can_edit_product
# EXPORTS: products_bp (Flask Blueprint)
# REQUIRED_BY: app.py
# DB_TABLES: products (id, tenant_id, name, sku, price_cents, stock_qty, deleted_at) | users (id, tenant_id, email, name, role, active, last_login)
# AGENT_RULES: admin check MUST use payload['role'] == 'admin'; NEVER use user['is_admin']
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *
from flask import Blueprint, request, jsonify
from core.auth import verify_token, require_auth, require_admin

products_bp = Blueprint('products', __name__, url_prefix='/api/products')

def create_product_route():
    # @REQUIRES-READ: core/auth.py → require_admin — use decorator instead of manual check
    # @SEE: core/auth.py AGENT_RULES — admin field is role NOT is_admin
    payload = verify_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    # BUG B3: checks user['is_admin'] but field is payload['role'] == 'admin'
    if not request.user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    data = request.json
    product = create(payload['tenant_id'], data)
    return jsonify(product), 201
