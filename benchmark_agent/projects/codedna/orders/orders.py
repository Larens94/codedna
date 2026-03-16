"""orders/orders.py -- Order lifecycle management.

Depends on: db/queries.py :: execute(), users/users.py :: get_user()
Exports:
    create_order(user_id, items) -> None
    get_active_orders() -> list[dict]
    get_order(order_id) -> dict
Used by: analytics/revenue.py :: get_revenue_rows(), views/dashboard.py :: render()

Rules:
  - orders.user_id è una FK su users.id.
  - Il sistema utenti usa soft delete (vedi users/users.py :: delete_user() e le sue Rules).
"""
from db.queries import execute

def create_order(user_id, items):
    execute("INSERT INTO orders (user_id, items) VALUES (?, ?)", (user_id, str(items)))

def get_active_orders():
    return execute("SELECT * FROM orders WHERE status != 'cancelled'")

def get_order(order_id):
    return execute("SELECT * FROM orders WHERE id = ?", (order_id,))
