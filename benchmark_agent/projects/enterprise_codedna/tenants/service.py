"""tenants/service.py — Service module.

deps:    tenants/models.py | subscriptions/models.py :: get_by_tenant | notifications/email.py :: send_suspension_notice
exports: onboard(name, plan, owner_email) -> dict | suspend(tenant_id, reason) -> None | reactivate(tenant_id) -> None | get_details(tenant_id) -> dict
used_by: api/admin.py | api/admin.py
tables:  tenants(id, plan, suspended_at, deleted_at) | subscriptions(id, tenant_id, plan, status, next_billing_at)
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def suspend(tenant_id: str, reason: str = ''):
    tenant = get_tenant(tenant_id)
    suspend_tenant(tenant_id)
    send_suspension_notice(tenant['owner_email'], tenant_id, reason)
