import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def full_monthly_report(year: int, month: int):
    rev = monthly_revenue(year, month)
    churn = churn_rate(year, month)
    usage = get_all_usage(month)
    return {'revenue': rev, 'churn_rate': churn, 'usage': usage}
