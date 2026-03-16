# === CODEDNA:0.5 ==============================================
# FILE: api/orders.py
# PURPOSE: Orders logic for api
# CONTEXT_BUDGET: normal
# DEPENDS_ON: orders/checkout.py :: checkout | orders/models.py :: list_orders | core/auth.py :: require_auth
# EXPORTS: orders_bp (Flask Blueprint)
# REQUIRED_BY: app.py
# DB_TABLES: orders (id, tenant_id, user_id, items, total_cents, status, created_at)
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

orders_bp = Blueprint('orders', __name__, url_prefix='/api/orders')

def checkout_route():
    payload = verify_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    data = request.json
    result = checkout(data['session_id'], payload['tenant_id'], payload['user_id'], data['payment_method'])
    return jsonify(result), 201
