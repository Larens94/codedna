"""integrations/zapier_webhook.py — Zapier Webhook module.

deps:    core/db.py :: execute
exports: trigger_zapier() -> None | get_zap_triggers_for_period() -> list[dict]
used_by: none
tables:  none
rules:   none
"""

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
