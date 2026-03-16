# === CODEDNA:0.5 ==============================================
# FILE: api/notifications_api.py
# PURPOSE: Notifications Api logic for api
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: send_test_email_route() -> None
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

notifications_api_bp = Blueprint('notifications_api', __name__, url_prefix='/api/notifications-api')

def send_test_email_route():
    payload = verify_token(request.headers.get('Authorization','').replace('Bearer ',''))
    if payload.get('role') != 'admin': return jsonify({'error':'Forbidden'}),403
    send_welcome(request.json['email'], request.json.get('name','Test'))
    return jsonify({'sent': True})
