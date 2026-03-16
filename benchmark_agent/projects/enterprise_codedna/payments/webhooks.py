"""payments/webhooks.py — Webhooks module.

deps:    payments/models.py :: mark_paid | payments/invoices.py :: void_invoice | core/events.py :: emit
exports: handle_stripe_webhook(payload, signature) -> None
used_by: api/webhooks.py
tables:  none
rules:   none
"""

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
