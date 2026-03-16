# === CODEDNA:0.5 ==============================================
# FILE: notifications/scheduler.py
# PURPOSE: Scheduler logic for notifications
# CONTEXT_BUDGET: normal
# DEPENDS_ON: notifications/email.py | analytics/revenue.py :: monthly_revenue
# EXPORTS: schedule_monthly_report() -> None | schedule_payment_reminders() -> None
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

def schedule_monthly_report():
    from datetime import datetime
    now = datetime.utcnow()
    report = monthly_revenue(now.year, now.month - 1 or 12)
    # send to all admin users
