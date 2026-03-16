# === CODEDNA:0.5 ==============================================
# FILE: users/permissions.py
# PURPOSE: Permissions logic for users
# CONTEXT_BUDGET: normal
# DEPENDS_ON: users/models.py :: get_user | tenants/models.py :: get_tenant
# EXPORTS: can_edit_product(user_id) -> bool | can_manage_users(user_id) -> bool | can_view_reports(user_id) -> bool | require_role(role) -> decorator
# REQUIRED_BY: api/products.py
# DB_TABLES: users (id, tenant_id, email, name, role, active, last_login) | tenants (id, name, plan, owner_email, suspended_at, deleted_at)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

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
