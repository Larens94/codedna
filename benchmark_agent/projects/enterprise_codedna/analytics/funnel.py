# === CODEDNA:0.5 ==============================================
# FILE: analytics/funnel.py
# PURPOSE: Funnel logic for analytics
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: cart_to_checkout_rate(tenant_id, days) -> float | checkout_to_order_rate(tenant_id, days) -> float
# REQUIRED_BY: none
# DB_TABLES: none
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def cart_to_checkout_rate(tenant_id: str, days: int = 30):
    carts = execute('SELECT COUNT(*) as n FROM events WHERE tenant_id=%s AND event=%s AND created_at > NOW()-%s::interval', (tenant_id, 'cart.created', f'{days} days'))
    checkouts = execute('SELECT COUNT(*) as n FROM events WHERE tenant_id=%s AND event=%s AND created_at > NOW()-%s::interval', (tenant_id, 'checkout.started', f'{days} days'))
    c = carts[0]['n'] if carts else 0
    return checkouts[0]['n'] / c if c else 0.0
