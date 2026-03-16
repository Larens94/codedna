"""models/discount_model.py — Discount Model module.

deps:    core/db.py :: execute
exports: get_discount() -> dict|None | list_active_discounts() -> list[dict] | create_discount() -> dict | deactivate_discount() -> None
used_by: none
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_discount(code:str):
    return execute_one('SELECT * FROM discounts WHERE code=%s', (code,))

def list_active_discounts(tenant_id:str):
    return execute('SELECT * FROM discounts WHERE tenant_id=%s AND active=TRUE AND expired_at > NOW()', (tenant_id,))

def create_discount(tenant_id:str, code:str, percentage:float, expires_at:str):
    return execute_one('INSERT INTO discounts (tenant_id,code,percentage,expired_at) VALUES (%s,%s,%s,%s) RETURNING *', (tenant_id,code,percentage,expires_at))

def deactivate_discount(code:str):
    execute('UPDATE discounts SET active=FALSE WHERE code=%s', (code,))
