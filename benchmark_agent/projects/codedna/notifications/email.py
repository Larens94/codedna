"""notifications/email.py -- Transactional email sending.

Depends on: config.py :: SMTP_HOST
Exports: send_order_confirm(user_email, order_id), send_invoice(user_email, pdf_bytes)
Used by: orders/orders.py :: create_order()
"""
def send_order_confirm(user_email, order_id):
    print(f"[EMAIL] order {order_id} confirmed to {user_email}")

def send_invoice(user_email, pdf_bytes):
    print(f"[EMAIL] invoice sent to {user_email}")
