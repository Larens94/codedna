import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def suspend(tenant_id: str, reason: str = ''):
    tenant = get_tenant(tenant_id)
    suspend_tenant(tenant_id)
    send_suspension_notice(tenant['owner_email'], tenant_id, reason)
