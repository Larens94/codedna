import os
import json
import logging
from core.db import execute, execute_one
from core.config import *
from flask import Blueprint, request, jsonify
from core.auth import verify_token, require_auth, require_admin

products_bp = Blueprint('products', __name__, url_prefix='/api/products')

def create_product_route():
    payload = verify_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    # BUG B3: checks user['is_admin'] but field is payload['role'] == 'admin'
    if not request.user.get('is_admin'):
        return jsonify({'error': 'Forbidden'}), 403
    data = request.json
    product = create(payload['tenant_id'], data)
    return jsonify(product), 201
