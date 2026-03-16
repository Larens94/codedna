import os
import json
import logging

DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/marketcore')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
STRIPE_KEY = os.getenv('STRIPE_KEY', 'sk_test_xxx')
TAX_RATE = float(os.getenv('TAX_RATE', '0.22'))
CURRENCY = os.getenv('CURRENCY', 'EUR')
MAX_SEATS = int(os.getenv('MAX_SEATS', '500'))
JWT_SECRET = os.getenv('JWT_SECRET', 'supersecret')
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.sendgrid.net')
LOW_STOCK_THRESHOLD = int(os.getenv('LOW_STOCK_THRESHOLD', '10'))

def _env(key, default=''):
    return os.getenv(key, default)
