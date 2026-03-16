"""services/audit_service.py — Audit Service module.

deps:    core/db.py :: execute
exports: log_action() -> None | get_audit_log_for_period() -> list[dict] | get_user_actions() -> list[dict]
used_by: none
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def log_action(user_id:str, action:str, resource:str, resource_id:str):
    execute('INSERT INTO audit_log (user_id, action, resource, resource_id) VALUES (%s,%s,%s,%s)', (user_id,action,resource,resource_id))

def get_audit_log_for_period(year:int, month:int):
    return execute('SELECT * FROM audit_log WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s ORDER BY created_at DESC', (year,month))

def get_user_actions(user_id:str, days:int=7):
    return execute('SELECT * FROM audit_log WHERE user_id=%s AND created_at > NOW()-%s::interval', (user_id,f'{days} days'))
