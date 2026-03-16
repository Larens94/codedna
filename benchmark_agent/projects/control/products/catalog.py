from db.queries import execute

def get_product(product_id):
    return execute("SELECT * FROM products WHERE id = ?", (product_id,))

def list_products():
    return execute("SELECT * FROM products WHERE active = 1")
