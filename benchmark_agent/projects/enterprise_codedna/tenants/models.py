# === CODEDNA:0.5 ==============================================
# FILE: tenants/models.py
# PURPOSE: Tenant CRUD with soft-suspend and soft-delete
# CONTEXT_BUDGET: always
# DEPENDS_ON: core/db.py :: execute | core/db.py :: execute_one
# EXPORTS: get_tenant(id) -> dict | None | list_active_tenants() -> list[dict] | create_tenant(name, plan, owner_email) -> dict | suspend_tenant(id) -> None | reactivate_tenant(id) -> None | delete_tenant(id) -> None | is_suspended(tenant) -> bool
# REQUIRED_BY: tenants/service.py | tenants/limits.py | tenants/billing.py
# DB_TABLES: tenants (id, name, plan, owner_email, suspended_at, deleted_at)
# AGENT_RULES: suspend = soft (suspended_at=NOW()); delete = soft (deleted_at=NOW()); rows stay in DB
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_tenant(tenant_id: str):
    return execute_one('SELECT * FROM tenants WHERE id = %s', (tenant_id,))

def list_active_tenants():
    return execute('SELECT * FROM tenants WHERE suspended_at IS NULL AND deleted_at IS NULL')

def suspend_tenant(tenant_id: str):
    execute('UPDATE tenants SET suspended_at = NOW() WHERE id = %s', (tenant_id,))

def is_suspended(tenant: dict):
    return tenant.get('suspended_at') is not None
