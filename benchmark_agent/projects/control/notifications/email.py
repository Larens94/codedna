def send_order_confirm(user_email, order_id):
    print(f"[EMAIL] order {order_id} confirmed to {user_email}")

def send_invoice(user_email, pdf_bytes):
    print(f"[EMAIL] invoice sent to {user_email}")
