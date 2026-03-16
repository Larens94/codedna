# === CODEDNA:0.5 ==============================================
# FILE: workers/report_generator.py
# PURPOSE: Report Generator logic for workers
# CONTEXT_BUDGET: normal
# DEPENDS_ON: analytics/reports.py :: full_monthly_report | notifications/email.py
# EXPORTS: generate_and_send(year, month) -> None
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

def generate_and_send(year: int, month: int):
    report = full_monthly_report(year, month)
    # send to admins
