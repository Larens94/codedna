# === CODEDNA:0.5 ==============================================
# FILE: payments/invoices.py
# PURPOSE: Invoice creation storing pre-taxed total
# CONTEXT_BUDGET: always
# DEPENDS_ON: payments/models.py :: create_invoice_record | core/config.py :: TAX_RATE
# EXPORTS: create_invoice(order_id, tenant_id, total_cents) -> dict | void_invoice(invoice_id) -> None
# REQUIRED_BY: tenants/billing.py | orders/checkout.py | payments/service.py
# DB_TABLES: none
# AGENT_RULES: total_cents arg is pre-taxed; do NOT re-apply TAX_RATE
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def create_invoice(order_id: str, tenant_id: str, total_cents: int):
    # @SEE: orders/checkout.py → checkout — tax already included in total_cents arg
    # total_cents already includes tax from orders/checkout.py
    return create_invoice_record(order_id, tenant_id, total_cents, 'outstanding')
