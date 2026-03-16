"""api/products.py — Product CRUD endpoints; admin check uses role not is_admin.

deps:    products/service.py | products/catalog.py | core/auth.py :: require_auth | users/permissions.py :: can_edit_product
exports: products_bp (Flask Blueprint)
used_by: app.py
tables:  products(id, tenant_id, price_cents, stock_qty, deleted_at) | users(id, tenant_id, email, role, active)
rules:   admin check MUST use payload['role'] == 'admin' from JWT → NEVER use request.user.get('is_admin')
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *
from flask import Blueprint, request, jsonify
from core.auth import verify_token, require_auth, require_admin

products_bp = Blueprint('products', __name__, url_prefix='/api/products')

def create_product_route():
    """Create a new product for the authenticated tenant.

    Rules:   Admin check MUST use payload['role'] == 'admin' from JWT.
             NEVER use request.user.get('is_admin') — that field does not exist.
    """
    payload = verify_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    # BUG B3: checks user['is_admin'] but field is payload['role'] == 'admin'  # BUG: 'is_admin' field doesn't exist in JWT; use payload['role'] == 'admin'
    if not request.user.get('is_admin'):  # BUG: 'is_admin' field doesn't exist in JWT; use payload['role'] == 'admin'
        return jsonify({'error': 'Forbidden'}), 403
    data = request.json
    product = create(payload['tenant_id'], data)
    return jsonify(product), 201
