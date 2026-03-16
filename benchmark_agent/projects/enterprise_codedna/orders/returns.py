"""orders/returns.py — Returns module.

deps:    orders/models.py :: get_order | products/inventory.py :: increment_stock | payments/service.py :: refund_payment
exports: initiate_return(order_id, items, reason) -> dict | approve_return(return_id) -> None | get_return(return_id) -> dict
used_by: none
tables:  orders(id, tenant_id, user_id, items, total_cents, status) | products(id, tenant_id, price_cents, stock_qty, deleted_at)
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def initiate_return(order_id: str, items: list, reason: str):
    order = get_order(order_id)
    if order['status'] != 'fulfilled': raise InvalidStatusError()
    return execute_one('INSERT INTO returns (order_id, items, reason, status) VALUES (%s,%s,%s,%s) RETURNING *', (order_id, json.dumps(items), reason, 'pending'))
