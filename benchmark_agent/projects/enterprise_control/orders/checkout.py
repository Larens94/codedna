import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def checkout(session_id: str, tenant_id: str, user_id: str, payment_method: str):
    cart = get_cart(session_id)
    if not cart['items']: raise EmptyCartError()
    subtotal = sum(get_price(i['product_id']) * i['qty'] for i in cart['items'])
    tax = round(subtotal * TAX_RATE)
    total = subtotal + tax
    order = create_order(tenant_id, user_id, cart['items'], total)
    invoice = create_invoice(order['id'], tenant_id, total)  # total already includes tax
    return {'order': order, 'invoice': invoice}
