# === CODEDNA:0.5 ==============================================
# FILE: workers/webhook_dispatcher.py
# PURPOSE: Webhook Dispatcher logic for workers
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: dispatch_all() -> None | dispatch_for_tenant() -> None
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

def dispatch_all(event:str, payload:dict):
    webhooks = execute('SELECT * FROM webhooks WHERE events @> %s::jsonb AND active=TRUE', (f'["{event}"]',))
    for wh in webhooks: _send(wh['url'], payload)

def dispatch_for_tenant(tenant_id:str, event:str, payload:dict):
    webhooks = execute('SELECT * FROM webhooks WHERE tenant_id=%s AND active=TRUE', (tenant_id,))
    for wh in webhooks: _send(wh['url'], payload)
