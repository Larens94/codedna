import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_shipments_for_period(year:int, month:int):
    return execute('SELECT * FROM shipments WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s', (year,month))

def get_delayed_shipments():
    return execute('SELECT * FROM shipments WHERE status=%s AND eta < NOW()', ('in_transit',))
