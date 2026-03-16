"""api/webhooks.py — Webhooks module.

deps:    payments/webhooks.py :: handle_stripe_webhook
exports: webhooks_bp (Flask Blueprint)
used_by: app.py
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

webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/api/webhooks')

def stripe_webhook_route():
    payload = request.get_data()
    signature = request.headers.get('Stripe-Signature')
    handle_stripe_webhook(payload, signature)
    return jsonify({'ok': True})
