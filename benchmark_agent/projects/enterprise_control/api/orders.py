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
