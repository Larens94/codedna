# === CODEDNA:0.5 ==============================================
# FILE: payments/webhooks.py
# PURPOSE: Webhooks logic for payments
# CONTEXT_BUDGET: normal
# DEPENDS_ON: payments/models.py :: mark_paid | payments/invoices.py :: void_invoice | core/events.py :: emit
# EXPORTS: handle_stripe_webhook(payload, signature) -> None
# REQUIRED_BY: api/webhooks.py
# DB_TABLES: none
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def handle_stripe_webhook(payload: bytes, signature: str):
    event = stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
    if event['type'] == 'payment_intent.succeeded':
        mark_paid(event['data']['object']['metadata']['invoice_id'], event['data']['object']['id'])
        emit('payment.received', event['data']['object'])
