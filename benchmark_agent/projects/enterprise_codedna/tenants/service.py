# === CODEDNA:0.5 ==============================================
# FILE: tenants/service.py
# PURPOSE: Service logic for tenants
# CONTEXT_BUDGET: normal
# DEPENDS_ON: tenants/models.py | subscriptions/models.py :: get_by_tenant | notifications/email.py :: send_suspension_notice
# EXPORTS: onboard(name, plan, owner_email) -> dict | suspend(tenant_id, reason) -> None | reactivate(tenant_id) -> None | get_details(tenant_id) -> dict
# REQUIRED_BY: api/admin.py | api/admin.py
# DB_TABLES: tenants (id, name, plan, owner_email, suspended_at, deleted_at) | subscriptions (id, tenant_id, plan, status, next_billing_at)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def suspend(tenant_id: str, reason: str = ''):
    tenant = get_tenant(tenant_id)
    suspend_tenant(tenant_id)
    send_suspension_notice(tenant['owner_email'], tenant_id, reason)
