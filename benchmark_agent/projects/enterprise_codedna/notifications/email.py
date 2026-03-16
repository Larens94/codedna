# === CODEDNA:0.5 ==============================================
# FILE: notifications/email.py
# PURPOSE: Email logic for notifications
# CONTEXT_BUDGET: always
# DEPENDS_ON: core/config.py :: SMTP_HOST | core/config.py :: LOW_STOCK_THRESHOLD
# EXPORTS: send_welcome(email, name) -> None | send_suspension_notice(email, tenant_id, reason) -> None | send_invoice_email(tenant_id, invoice) -> None | send_payment_failed(email, invoice_id) -> None | send_low_stock_alert(tenant_id, product_id, current_qty) -> None
# REQUIRED_BY: tenants/service.py | users/service.py | notifications/scheduler.py
# DB_TABLES: none
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def send_low_stock_alert(tenant_id: str, product_id: str, current_qty: int):
    # TODO T3: send alert to tenant owner email
    pass

def send_welcome(email: str, name: str):
    _send(email, f'Welcome {name}!', '<p>Your account is ready.</p>')

def send_suspension_notice(email: str, tenant_id: str, reason: str = ''):
    _send(email, 'Account Suspended', f'<p>Account {tenant_id} suspended. Reason: {reason}</p>')
