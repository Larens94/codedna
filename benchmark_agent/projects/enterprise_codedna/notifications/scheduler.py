"""notifications/scheduler.py — Scheduler module.

deps:    notifications/email.py | analytics/revenue.py :: monthly_revenue
exports: schedule_monthly_report() -> None | schedule_payment_reminders() -> None
used_by: none
tables:  none
rules:   none
"""

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
