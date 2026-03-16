"""config.py -- Environment-based configuration loader.

Exports: DATABASE_URL, REDIS_URL, STRIPE_KEY, SENDGRID_KEY, JWT_SECRET,
         MAX_SEATS, BILLING_DAY, TAX_RATE, CURRENCY, ENV
Used by: db/connection.py, services/stripe_service.py, notifications/email.py

Rules:
  - Never hardcode secrets. All values come from environment variables.
  - TAX_RATE is a float (0.22 = 22%). Already applied in billing_service.py.
"""
import os

DATABASE_URL   = os.getenv("DATABASE_URL", "postgresql://localhost/saas_db")
REDIS_URL      = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STRIPE_KEY     = os.getenv("STRIPE_KEY", "sk_test_xxx")
SENDGRID_KEY   = os.getenv("SENDGRID_KEY", "SG.xxx")
JWT_SECRET     = os.getenv("JWT_SECRET", "supersecret")
MAX_SEATS      = int(os.getenv("MAX_SEATS", "500"))
BILLING_DAY    = int(os.getenv("BILLING_DAY", "1"))
TAX_RATE       = float(os.getenv("TAX_RATE", "0.22"))
CURRENCY       = os.getenv("CURRENCY", "EUR")
ENV            = os.getenv("ENV", "development")
