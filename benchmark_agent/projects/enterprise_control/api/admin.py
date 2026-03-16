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
