"""models/audit_model.py — Audit Model module.

deps:    core/db.py :: execute
exports: get_audit_entries() -> list[dict] | get_audit_for_period() -> list[dict]
used_by: none
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_audit_entries(resource_id:str):
    return execute('SELECT * FROM audit_log WHERE resource_id=%s ORDER BY created_at DESC', (resource_id,))

def get_audit_for_period(year:int, month:int):
    return execute('SELECT * FROM audit_log WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))
