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
