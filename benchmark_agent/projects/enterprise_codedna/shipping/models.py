"""shipping/models.py — Models module.

deps:    core/db.py :: execute | core/db.py :: execute_one
exports: create_shipment(order_id, carrier, tracking) -> dict | get_shipment(order_id) -> dict | None | update_tracking(shipment_id, status) -> None
used_by: shipping/service.py | shipping/tracking.py
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def create_shipment(order_id: str, carrier: str, tracking: str):
    return execute_one('INSERT INTO shipments (order_id, carrier, tracking_number) VALUES (%s,%s,%s) RETURNING *', (order_id, carrier, tracking))
