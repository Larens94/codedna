import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def on_payment_succeeded(event:dict):
    invoice_id = event['data']['object']['metadata'].get('invoice_id')
    if invoice_id: execute('UPDATE invoices SET status=%s WHERE id=%s', ('paid',invoice_id))

def on_subscription_cancelled(event:dict):
    sub_id = event['data']['object']['id']
    execute('UPDATE subscriptions SET status=%s WHERE stripe_subscription_id=%s', ('cancelled',sub_id))

def get_webhook_logs_for_period(year:int, month:int):
    return execute('SELECT * FROM stripe_webhook_log WHERE EXTRACT(YEAR FROM received_at)=%s AND EXTRACT(MONTH FROM received_at)=%s', (year,month))
