"""shipping/service.py — Service module.

deps:    shipping/models.py | shipping/carriers.py :: book_shipment | orders/models.py :: update_status
exports: ship_order(order_id, carrier) -> dict | get_tracking_info(order_id) -> dict
used_by: none
tables:  orders(id, tenant_id, user_id, items, total_cents, status)
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def ship_order(order_id: str, carrier: str):
    booking = book_shipment(order_id, carrier)
    shipment = create_shipment(order_id, carrier, booking['tracking'])
    update_status(order_id, 'shipped')
    return shipment
