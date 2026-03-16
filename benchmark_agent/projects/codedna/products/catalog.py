"""products/catalog.py -- Product catalog.

Depends on: db/queries.py :: execute()
Exports: get_product(id) -> dict, list_products() -> list
Used by: orders/orders.py, views/dashboard.py
"""
from db.queries import execute

def get_product(product_id):
    return execute("SELECT * FROM products WHERE id = ?", (product_id,))

def list_products():
    return execute("SELECT * FROM products WHERE active = 1")
