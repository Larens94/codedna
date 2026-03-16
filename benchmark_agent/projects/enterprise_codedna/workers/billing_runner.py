# === CODEDNA:0.5 ==============================================
# FILE: workers/billing_runner.py
# PURPOSE: Billing Runner logic for workers
# CONTEXT_BUDGET: normal
# DEPENDS_ON: tenants/billing.py :: bill_all_tenants
# EXPORTS: run(year, month) -> list[dict]
# REQUIRED_BY: none
# DB_TABLES: tenants (id, name, plan, owner_email, suspended_at, deleted_at)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def run(year: int | None = None, month: int | None = None):
    from datetime import datetime
    now = datetime.utcnow()
    return bill_all_tenants(year or now.year, month or now.month)
