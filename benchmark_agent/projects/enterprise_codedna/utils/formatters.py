# === CODEDNA:0.5 ==============================================
# FILE: utils/formatters.py
# PURPOSE: Formatters logic for utils
# CONTEXT_BUDGET: minimal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: format_currency() -> str | format_period() -> str | format_tenant_id() -> str
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

def format_currency(amount_cents:int, currency:str='EUR'):
    return f'{amount_cents/100:.2f} {currency}'

def format_period(year:int, month:int):
    import calendar
    return f'{calendar.month_name[month]} {year}'

def format_tenant_id(tenant_id:str):
    return f'T-{tenant_id[:8].upper()}'
