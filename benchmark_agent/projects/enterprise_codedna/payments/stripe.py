"""payments/stripe.py — Stripe module.

deps:    core/config.py :: STRIPE_KEY
exports: charge_card(amount_cents, payment_method) -> dict | refund_charge(charge_id, amount_cents) -> dict | create_customer(email, name) -> str
used_by: payments/service.py | payments/refunds.py
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def charge_card(amount_cents: int, payment_method: str):
    intent = stripe.PaymentIntent.create(amount=amount_cents, currency='eur', payment_method=payment_method, confirm=True)
    return {'id': intent.id, 'status': intent.status}
