from db.queries import execute

def create_order(user_id, items):
    execute("INSERT INTO orders (user_id, items) VALUES (?, ?)", (user_id, str(items)))

def get_active_orders():
    return execute("SELECT * FROM orders WHERE status != 'cancelled'")

def get_order(order_id):
    return execute("SELECT * FROM orders WHERE id = ?", (order_id,))
