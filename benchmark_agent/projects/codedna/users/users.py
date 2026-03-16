"""users/users.py -- User CRUD operations.

Depends on: db/queries.py :: execute()
Exports:
    get_user_by_email(email) -> dict
    get_user(user_id) -> dict
    delete_user(user_id) -> None
    create_user(data) -> None
Used by: auth/login.py, orders/orders.py

Rules:
  - Il sistema usa SOFT DELETE: delete_user() imposta users.deleted_at = NOW().
    La riga rimane nel database. Gli utenti eliminati hanno deleted_at IS NOT NULL.
  - Chi legge o aggrega dati deve considerare se includere utenti con deleted_at != NULL.
"""
from db.queries import execute

def get_user_by_email(email):
    return execute("SELECT * FROM users WHERE email = ? AND deleted_at IS NULL", (email,))

def get_user(user_id):
    return execute("SELECT * FROM users WHERE id = ?", (user_id,))

def delete_user(user_id):
    execute("UPDATE users SET deleted_at = NOW() WHERE id = ?", (user_id,))

def create_user(data):
    execute("INSERT INTO users (email, name) VALUES (?, ?)",
            (data["email"], data["name"]))
