"""integrations/slack_notifier.py — Slack Notifier module.

deps:    core/db.py :: execute
exports: send_slack() -> None | notify_new_order() -> None
used_by: none
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def send_slack(webhook_url:str, message:str):
    import urllib.request,json
    data = json.dumps({'text':message}).encode()
    urllib.request.urlopen(urllib.request.Request(webhook_url,data,{'Content-Type':'application/json'}))

def notify_new_order(tenant_id:str, order_id:str, amount_cents:int):
    cfg = execute_one('SELECT slack_webhook FROM tenant_settings WHERE tenant_id=%s', (tenant_id,))
    if cfg and cfg['slack_webhook']: send_slack(cfg['slack_webhook'],f'New order {order_id}: {amount_cents/100:.2f}€')
