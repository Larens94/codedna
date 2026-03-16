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
