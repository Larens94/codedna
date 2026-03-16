"""admin/user_management.py — User Management module.

deps:    core/db.py :: execute
exports: list_all_users() -> dict | get_suspended_users() -> list[dict] | deactivate_all_tenant_users() -> int
used_by: none
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def list_all_users(page:int=1, per_page:int=50):
    offset = (page-1)*per_page
    users = execute('SELECT * FROM users WHERE active=TRUE ORDER BY created_at DESC LIMIT %s OFFSET %s', (per_page,offset))
    return {'users':users,'page':page}

def get_suspended_users():
    return execute('SELECT u.* FROM users u JOIN tenants t ON u.tenant_id=t.id WHERE t.suspended_at IS NOT NULL AND u.active=TRUE')

def deactivate_all_tenant_users(tenant_id:str):
    execute('UPDATE users SET active=FALSE WHERE tenant_id=%s', (tenant_id,))
    return execute_one('SELECT COUNT(*) as n FROM users WHERE tenant_id=%s', (tenant_id,))['n']
