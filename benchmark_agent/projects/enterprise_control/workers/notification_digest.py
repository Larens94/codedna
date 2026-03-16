import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def send_daily_digest(tenant_id:str):
    orders_today = execute('SELECT COUNT(*) as n FROM orders WHERE tenant_id=%s AND DATE(created_at)=CURRENT_DATE', (tenant_id,))
    pass  # format and send

def send_weekly_summary(tenant_id:str):
    revenue = execute_one('SELECT SUM(amount_cents) as total FROM invoices WHERE tenant_id=%s AND created_at > NOW()-INTERVAL \'7 days\'', (tenant_id,))
    pass  # send email
