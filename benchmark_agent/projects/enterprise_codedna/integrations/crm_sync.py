# === CODEDNA:0.5 ==============================================
# FILE: integrations/crm_sync.py
# PURPOSE: Crm Sync logic for integrations
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: sync_tenant_to_crm() -> None | list_active_crm_syncs() -> list[dict]
# REQUIRED_BY: none
# DB_TABLES: none
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

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
