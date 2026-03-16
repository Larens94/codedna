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
