"""reports/product_performance.py — Product Performance module.

deps:    core/db.py :: execute
exports: get_top_products() -> list[dict] | get_products_for_period() -> list[dict]
used_by: none
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_top_products(tenant_id:str, limit:int=10):
    return execute('SELECT product_id, SUM(qty) as total FROM order_items WHERE tenant_id=%s GROUP BY product_id ORDER BY total DESC LIMIT %s', (tenant_id, limit))

def get_products_for_period(year:int, month:int):
    return execute('SELECT * FROM order_items WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))
