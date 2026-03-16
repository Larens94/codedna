# === CODEDNA:0.5 ==============================================
# FILE: reports/shipping_report.py
# PURPOSE: Shipping Report logic for reports
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: get_shipments_for_period() -> list[dict] | get_delayed_shipments() -> list[dict]
# REQUIRED_BY: none
# DB_TABLES: none
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_shipments_for_period(year:int, month:int):
    return execute('SELECT * FROM shipments WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))

def get_delayed_shipments():
    return execute('SELECT * FROM shipments WHERE status=%s AND eta < NOW()', ('in_transit',))
