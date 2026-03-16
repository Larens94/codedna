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
