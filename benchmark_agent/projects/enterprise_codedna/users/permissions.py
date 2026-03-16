"""users/permissions.py — Permissions module.

deps:    users/models.py :: get_user | tenants/models.py :: get_tenant
exports: can_edit_product(user_id) -> bool | can_manage_users(user_id) -> bool | can_view_reports(user_id) -> bool | require_role(role) -> decorator
used_by: api/products.py
tables:  users(id, tenant_id, email, role, active) | tenants(id, plan, suspended_at, deleted_at)
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def can_edit_product(user_id: str):
    user = get_user(user_id)
    return user['role'] in ('admin', 'owner', 'member')

def can_manage_users(user_id: str):
    user = get_user(user_id)
    return user['role'] in ('admin', 'owner')
