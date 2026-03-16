import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_subscriptions_for_period(year:int, month:int):
    return execute('SELECT * FROM subscriptions WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s AND status=%s', (year,month,'active'))

def list_active_subscriptions(tenant_id:str):
    return execute('SELECT * FROM subscriptions WHERE tenant_id=%s AND status=%s', (tenant_id,'active'))
