# === CODEDNA:0.5 ==============================================
# FILE: shipping/service.py
# PURPOSE: Service logic for shipping
# CONTEXT_BUDGET: normal
# DEPENDS_ON: shipping/models.py | shipping/carriers.py :: book_shipment | orders/models.py :: update_status
# EXPORTS: ship_order(order_id, carrier) -> dict | get_tracking_info(order_id) -> dict
# REQUIRED_BY: none
# DB_TABLES: orders (id, tenant_id, user_id, items, total_cents, status, created_at)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

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
