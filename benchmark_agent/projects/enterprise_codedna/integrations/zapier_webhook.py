# === CODEDNA:0.5 ==============================================
# FILE: integrations/zapier_webhook.py
# PURPOSE: Zapier Webhook logic for integrations
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: trigger_zapier() -> None | get_zap_triggers_for_period() -> list[dict]
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

def trigger_zapier(tenant_id:str, event:str, data:dict):
    zaps = execute('SELECT url FROM zap_connections WHERE tenant_id=%s AND event=%s AND active=TRUE', (tenant_id,event))
    for z in zaps: pass  # POST to z['url']

def get_zap_triggers_for_period(year:int, month:int):
    return execute('SELECT * FROM zap_trigger_log WHERE EXTRACT(YEAR FROM triggered_at)=%s AND EXTRACT(MONTH FROM triggered_at)=%s', (year,month))
