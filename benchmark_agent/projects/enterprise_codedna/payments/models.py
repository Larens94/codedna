"""payments/models.py — Invoice CRUD; get_invoices_for_period has no tenant filter.

deps:    core/db.py :: execute | core/db.py :: execute_one
exports: get_invoice(id) -> dict | None | get_invoices_by_tenant(tenant_id) -> list[dict] | get_invoices_for_period(year, month) -> list[dict] | create_invoice_record(order_id, tenant_id, amount_cents, status) -> dict
used_by: payments/invoices.py | payments/service.py | payments/webhooks.py
tables:  none
rules:   get_invoices_for_period() no suspended_at filter → callers that aggregate revenue must filter
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_invoices_for_period(year: int, month: int):
    return execute('SELECT * FROM invoices WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year, month))
