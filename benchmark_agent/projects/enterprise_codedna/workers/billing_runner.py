"""workers/billing_runner.py — Billing Runner module.

deps:    tenants/billing.py :: bill_all_tenants
exports: run(year, month) -> list[dict]
used_by: none
tables:  tenants(id, plan, suspended_at, deleted_at)
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def run(year: int | None = None, month: int | None = None):
    from datetime import datetime
    now = datetime.utcnow()
    return bill_all_tenants(year or now.year, month or now.month)
