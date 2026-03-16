# === CODEDNA:0.5 ==============================================
# FILE: utils/pagination.py
# PURPOSE: Pagination logic for utils
# CONTEXT_BUDGET: minimal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: paginate() -> dict
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

def paginate(query:str, params:tuple, page:int=1, per_page:int=20):
    offset = (page-1)*per_page
    rows = execute(f'{query} LIMIT %s OFFSET %s', params+(per_page,offset))
    total = execute_one(f'SELECT COUNT(*) as n FROM ({query}) sub', params)
    return {'data':rows,'page':page,'per_page':per_page,'total':total['n']}
