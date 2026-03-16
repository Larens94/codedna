"""api/discounts_api.py — Discounts Api module.

deps:    core/db.py :: execute
exports: create_discount_route() -> None | validate_discount_route() -> None
used_by: none
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *
from flask import Blueprint, request, jsonify
from core.auth import verify_token, require_auth, require_admin

discounts_api_bp = Blueprint('discounts_api', __name__, url_prefix='/api/discounts-api')

def create_discount_route():
    data = request.json
    payload = verify_token(request.headers.get('Authorization','').replace('Bearer ',''))
    if payload.get('role') not in ('admin','owner'): return jsonify({'error':'Forbidden'}),403
    discount = create_discount(payload['tenant_id'],data['code'],data['percentage'],data['expires_at'])
    return jsonify(discount),201

def validate_discount_route():
    code = request.json.get('code')
    tenant_id = request.user['tenant_id']
    valid = validate_discount_code(code, tenant_id)
    return jsonify({'valid': valid})
