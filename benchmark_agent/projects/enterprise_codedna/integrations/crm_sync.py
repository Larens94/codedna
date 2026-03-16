"""integrations/crm_sync.py — Crm Sync module.

deps:    core/db.py :: execute
exports: sync_tenant_to_crm() -> None | list_active_crm_syncs() -> list[dict]
used_by: none
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def sync_tenant_to_crm(tenant_id:str):
    tenant = execute_one('SELECT * FROM tenants WHERE id=%s AND suspended_at IS NULL', (tenant_id,))
    if tenant: pass  # sync to CRM

def list_active_crm_syncs():
    return execute('SELECT * FROM crm_sync_log WHERE status=%s ORDER BY created_at DESC LIMIT 100', ('active',))
