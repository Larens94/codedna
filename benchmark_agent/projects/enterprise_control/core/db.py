import os
import json
import logging
from core.config import *

import psycopg2
_pool = None
def _get_conn():
    global _pool
    if _pool is None: _pool = psycopg2.connect(DB_URL)
    return _pool

def execute(sql: str, params: tuple = ()):
    cur = _get_conn().cursor()
    cur.execute(sql, params)
    if cur.description:
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    _get_conn().commit(); return []

def execute_one(sql: str, params: tuple = ()):
    rows = execute(sql, params)
    return rows[0] if rows else None
