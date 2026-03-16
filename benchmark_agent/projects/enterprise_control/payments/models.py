import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_invoices_for_period(year: int, month: int):
    return execute('SELECT * FROM invoices WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year, month))
