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
