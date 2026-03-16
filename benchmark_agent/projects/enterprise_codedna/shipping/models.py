# === CODEDNA:0.5 ==============================================
# FILE: shipping/models.py
# PURPOSE: Models logic for shipping
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute | core/db.py :: execute_one
# EXPORTS: create_shipment(order_id, carrier, tracking) -> dict | get_shipment(order_id) -> dict | None | update_tracking(shipment_id, status) -> None
# REQUIRED_BY: shipping/service.py | shipping/tracking.py
# DB_TABLES: none
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def create_shipment(order_id: str, carrier: str, tracking: str):
    return execute_one('INSERT INTO shipments (order_id, carrier, tracking_number) VALUES (%s,%s,%s) RETURNING *', (order_id, carrier, tracking))
