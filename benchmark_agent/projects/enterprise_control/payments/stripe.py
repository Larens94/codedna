import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def charge_card(amount_cents: int, payment_method: str):
    intent = stripe.PaymentIntent.create(amount=amount_cents, currency='eur', payment_method=payment_method, confirm=True)
    return {'id': intent.id, 'status': intent.status}
