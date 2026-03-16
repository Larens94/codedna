# === CODEDNA:0.5 ==============================================
# FILE: models/webhook_model.py
# PURPOSE: Webhook Model logic for models
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: list_webhooks() -> list[dict] | get_webhook_deliveries_for_period() -> list[dict] | create_webhook() -> dict
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

def list_webhooks(tenant_id:str):
    return execute('SELECT * FROM webhooks WHERE tenant_id=%s AND active=TRUE', (tenant_id,))

def get_webhook_deliveries_for_period(year:int, month:int):
    return execute('SELECT * FROM webhook_deliveries WHERE EXTRACT(YEAR FROM sent_at)=%s AND EXTRACT(MONTH FROM sent_at)=%s', (year,month))

def create_webhook(tenant_id:str, url:str, events:list):
    return execute_one('INSERT INTO webhooks (tenant_id,url,events) VALUES (%s,%s,%s) RETURNING *', (tenant_id,url,str(events)))
