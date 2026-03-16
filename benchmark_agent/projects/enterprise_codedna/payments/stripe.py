# === CODEDNA:0.5 ==============================================
# FILE: payments/stripe.py
# PURPOSE: Stripe logic for payments
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/config.py :: STRIPE_KEY
# EXPORTS: charge_card(amount_cents, payment_method) -> dict | refund_charge(charge_id, amount_cents) -> dict | create_customer(email, name) -> str
# REQUIRED_BY: payments/service.py | payments/refunds.py
# DB_TABLES: none
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def charge_card(amount_cents: int, payment_method: str):
    intent = stripe.PaymentIntent.create(amount=amount_cents, currency='eur', payment_method=payment_method, confirm=True)
    return {'id': intent.id, 'status': intent.status}
