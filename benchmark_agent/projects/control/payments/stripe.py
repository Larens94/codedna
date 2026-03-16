import os
STRIPE_KEY = os.getenv("STRIPE_KEY")

def charge(amount_cents, token):
    return {"status": "ok", "charge_id": "ch_test"}

def refund(charge_id):
    return {"status": "refunded"}
