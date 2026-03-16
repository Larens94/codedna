import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_order(order_id: str):
    return execute_one('SELECT * FROM orders WHERE id = %s', (order_id,))

def get_orders_for_period(year: int, month: int):
    return execute('SELECT * FROM orders WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year, month))
