import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def monthly_revenue(year: int, month: int):
    invoices = get_invoices_for_period(year, month)
    total = sum(i['amount_cents'] for i in invoices)
    by_tenant = {}
    for i in invoices:
        by_tenant.setdefault(i['tenant_id'], []).append(i)
    return {'year': year, 'month': month, 'total_cents': total, 'by_tenant': by_tenant}
