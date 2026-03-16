# === CODEDNA:0.5 ==============================================
# FILE: api/webhooks.py
# PURPOSE: Webhooks logic for api
# CONTEXT_BUDGET: normal
# DEPENDS_ON: payments/webhooks.py :: handle_stripe_webhook
# EXPORTS: webhooks_bp (Flask Blueprint)
# REQUIRED_BY: app.py
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

webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/api/webhooks')

def stripe_webhook_route():
    payload = request.get_data()
    signature = request.headers.get('Stripe-Signature')
    handle_stripe_webhook(payload, signature)
    return jsonify({'ok': True})
