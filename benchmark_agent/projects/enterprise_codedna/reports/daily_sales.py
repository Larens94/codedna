"""reports/daily_sales.py — Daily Sales module.

deps:    core/db.py :: execute
exports: get_sales_for_period() -> list[dict] | get_daily_totals() -> dict
used_by: none
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_sales_for_period(year:int, month:int, day:int):
    return execute('SELECT * FROM sales WHERE date=%s', (f'{year}-{month:02d}-{day:02d}',))

def get_daily_totals(year:int, month:int):
    rows = execute('SELECT day, SUM(amount) FROM sales GROUP BY day WHERE month=%s', (month,))
    return {r['day']: r['sum'] for r in rows}
