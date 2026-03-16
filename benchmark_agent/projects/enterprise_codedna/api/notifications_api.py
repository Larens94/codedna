"""api/notifications_api.py — Notifications Api module.

deps:    core/db.py :: execute
exports: send_test_email_route() -> None
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

notifications_api_bp = Blueprint('notifications_api', __name__, url_prefix='/api/notifications-api')

def send_test_email_route():
    payload = verify_token(request.headers.get('Authorization','').replace('Bearer ',''))
    if payload.get('role') != 'admin': return jsonify({'error':'Forbidden'}),403
    send_welcome(request.json['email'], request.json.get('name','Test'))
    return jsonify({'sent': True})
