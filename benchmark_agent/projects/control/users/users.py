from db.queries import execute

def get_user_by_email(email):
    return execute("SELECT * FROM users WHERE email = ?", (email,))

def get_user(user_id):
    return execute("SELECT * FROM users WHERE id = ?", (user_id,))

def delete_user(user_id):
    # Soft delete: mantiene la riga, imposta deleted_at
    execute("UPDATE users SET deleted_at = NOW() WHERE id = ?", (user_id,))

def create_user(data):
    execute("INSERT INTO users (email, name) VALUES (?, ?)",
            (data["email"], data["name"]))
