"""db/connection.py -- PostgreSQL connection pool and SQL executor.

Depends on: config.py :: DATABASE_URL
Exports: execute(sql, params) -> list[dict], execute_one(sql, params) -> dict | None
Used by: (quasi tutti i modelli e service del progetto)

Rules:
  - Usare SEMPRE query parametrizzate: execute(sql, (p1, p2)).
  - execute() è thread-safe grazie al pool interno.
"""
import psycopg2
from config import DATABASE_URL

_pool = None

def get_conn():
    global _pool
    if _pool is None:
        _pool = psycopg2.connect(DATABASE_URL)
    return _pool

def execute(sql: str, params: tuple = ()) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    if cur.description:
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.commit()
    return []

def execute_one(sql: str, params: tuple = ()) -> dict | None:
    rows = execute(sql, params)
    return rows[0] if rows else None
