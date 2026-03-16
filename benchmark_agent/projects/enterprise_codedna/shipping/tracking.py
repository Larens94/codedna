"""shipping/tracking.py — Tracking module.

deps:    shipping/models.py :: get_shipment | shipping/carriers.py
exports: get_status(order_id) -> dict | webhook_update(carrier, payload) -> None
used_by: none
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_status(order_id: str):
    shipment = get_shipment(order_id)
    if not shipment: return {'status': 'not_shipped'}
    return {'status': shipment['status'], 'tracking': shipment['tracking_number']}
