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
