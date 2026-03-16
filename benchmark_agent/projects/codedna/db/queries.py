"""db/queries.py -- Low-level SQL executor.

Depends on: config.py :: DB_URL
Exports:
    execute(sql, params) -> list[dict]
Used by: users/users.py, orders/orders.py, analytics/revenue.py

Rules:
  - Usare SEMPRE query parametrizzate: execute(sql, (p1, p2)).
  - Non mai interpolate user input direttamente nella stringa SQL.
"""
import sqlite3

_conn = None

def _get_conn():
    global _conn
    if not _conn:
        _conn = sqlite3.connect(":memory:")
    return _conn

def execute(sql, params=()):
    cur = _get_conn().execute(sql, params)
    return [dict(zip([d[0] for d in cur.description or []], row))
            for row in cur.fetchall()]
