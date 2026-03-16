# === CODEDNA:0.5 ==============================================
# FILE: shipping/tracking.py
# PURPOSE: Tracking logic for shipping
# CONTEXT_BUDGET: normal
# DEPENDS_ON: shipping/models.py :: get_shipment | shipping/carriers.py
# EXPORTS: get_status(order_id) -> dict | webhook_update(carrier, payload) -> None
# REQUIRED_BY: none
# DB_TABLES: none
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_status(order_id: str):
    shipment = get_shipment(order_id)
    if not shipment: return {'status': 'not_shipped'}
    return {'status': shipment['status'], 'tracking': shipment['tracking_number']}
