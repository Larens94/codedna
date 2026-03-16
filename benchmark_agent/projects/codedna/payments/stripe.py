"""payments/stripe.py -- Stripe payment gateway.

Depends on: config.py :: STRIPE_KEY
Exports: charge(amount_cents, token) -> dict, refund(charge_id) -> dict
Used by: orders/orders.py :: create_order()

Rules:
  - amount_cents in CENTESIMI interi (es. 1999 = 19.99 EUR).
"""
import os
STRIPE_KEY = os.getenv("STRIPE_KEY")

def charge(amount_cents, token):
    return {"status": "ok", "charge_id": "ch_test"}

def refund(charge_id):
    return {"status": "refunded"}
