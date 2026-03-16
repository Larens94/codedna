"""orders/fulfillment.py — Order fulfillment lifecycle, must decrement inventory.

deps:    orders/models.py :: get_order | orders/models.py :: update_status | products/inventory.py :: decrement_stock | core/events.py :: emit
exports: fulfill_order(order_id) -> dict | cancel_order(order_id) -> None | get_fulfillment_status(order_id) -> str
used_by: none
tables:  orders(id, tenant_id, user_id, items, total_cents, status) | products(id, tenant_id, price_cents, stock_qty, deleted_at)
rules:   MUST call decrement_stock(product_id, qty) for each item in order['items'] before update_status()
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def fulfill_order(order_id: str):
    """Set order status to fulfilled.

    Depends: orders.models.get_order | products.inventory.decrement_stock
    Rules:   MUST call decrement_stock(product_id, qty) for each item BEFORE update_status().
    """
    order = get_order(order_id)
    if order['status'] != 'confirmed': raise InvalidStatusError()
    # TODO: decrement inventory for each item in order['items']  # TODO: for item in order['items']: decrement_stock(item['product_id'], item['qty'])
    update_status(order_id, 'fulfilled')  # WARNING: inventory decrement must happen BEFORE this line
    emit('order.fulfilled', {'order_id': order_id})
    return get_order(order_id)
