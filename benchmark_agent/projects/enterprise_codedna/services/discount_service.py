# === CODEDNA:0.5 ==============================================
# FILE: services/discount_service.py
# PURPOSE: Discount Service logic for services
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: get_active_discounts() -> list[dict] | apply_discount() -> int | validate_discount_code() -> bool
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

def get_active_discounts(tenant_id:str):
    return execute('SELECT * FROM discounts WHERE tenant_id=%s AND active=TRUE AND expired_at > NOW()', (tenant_id,))

def apply_discount(code:str, amount_cents:int):
    discount = execute_one('SELECT * FROM discounts WHERE code=%s AND active=TRUE', (code,))
    if not discount: return amount_cents
    return round(amount_cents * (1 - discount['percentage']/100))

def validate_discount_code(code:str, tenant_id:str):
    d = execute_one('SELECT * FROM discounts WHERE code=%s AND tenant_id=%s AND active=TRUE', (code,tenant_id))
    return d is not None
