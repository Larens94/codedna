# === CODEDNA:0.5 ==============================================
# FILE: payments/models.py
# PURPOSE: Models logic for payments
# CONTEXT_BUDGET: always
# DEPENDS_ON: core/db.py :: execute | core/db.py :: execute_one
# EXPORTS: get_invoice(id) -> dict | None | get_invoices_by_tenant(tenant_id) -> list[dict] | get_invoices_for_period(year, month) -> list[dict] | create_invoice_record(order_id, tenant_id, amount_cents, status) -> dict | mark_paid(invoice_id, charge_id) -> None
# REQUIRED_BY: payments/invoices.py | payments/service.py | payments/webhooks.py
# DB_TABLES: none
# AGENT_RULES: get_invoices_for_period does NOT filter suspended tenants; callers must filter if needed
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_invoices_for_period(year: int, month: int):
    return execute('SELECT * FROM invoices WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year, month))
