import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def run(year: int | None = None, month: int | None = None):
    from datetime import datetime
    now = datetime.utcnow()
    return bill_all_tenants(year or now.year, month or now.month)
