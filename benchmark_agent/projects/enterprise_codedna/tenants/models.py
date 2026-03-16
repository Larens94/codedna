"""tenants/models.py — Tenant CRUD with soft-suspend and soft-delete.

deps:    core/db.py :: execute | core/db.py :: execute_one
exports: get_tenant(id) -> dict | None | list_active_tenants() -> list[dict] | create_tenant(name, plan, owner_email) -> dict | suspend_tenant(id) -> None
used_by: tenants/service.py | tenants/limits.py | tenants/billing.py
tables:  tenants(id, plan, suspended_at, deleted_at)
rules:   soft-suspend: suspended_at=NOW() row stays in DB; soft-delete: deleted_at=NOW(); queries that aggregate must filter both
"""

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
