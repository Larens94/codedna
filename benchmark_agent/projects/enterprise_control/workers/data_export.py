import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def export_tenant_data(tenant_id:str):
    return {'orders': execute('SELECT * FROM orders WHERE tenant_id=%s', (tenant_id,)), 'invoices': execute('SELECT * FROM invoices WHERE tenant_id=%s', (tenant_id,))}

def scheduled_export(year:int, month:int):
    tenants = execute('SELECT id FROM tenants WHERE suspended_at IS NULL AND deleted_at IS NULL')
    for t in tenants: export_tenant_data(t['id'])
