import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def bill_all_tenants(year: int, month: int):
    tenants = list_active_tenants()
    results = []
    for t in tenants:
        try: results.append(bill_tenant(t['id'], year, month))
        except Exception as e: log(f'Billing failed for {t["id"]}: {e}')
    return results
