import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_churned_tenants_for_period(year:int, month:int):
    return execute('SELECT * FROM tenants WHERE EXTRACT(YEAR FROM deleted_at)=%s AND EXTRACT(MONTH FROM deleted_at)=%s', (year,month))

def get_suspension_stats():
    total = execute_one('SELECT COUNT(*) as n FROM tenants WHERE suspended_at IS NOT NULL')
    return {'suspended': total['n']}
