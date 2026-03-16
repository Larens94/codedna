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
