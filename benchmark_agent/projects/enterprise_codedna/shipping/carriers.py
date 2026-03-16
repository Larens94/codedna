"""shipping/carriers.py — Carriers module.

deps:    core/config.py
exports: book_shipment(order_id, carrier) -> dict | get_rates(origin, destination, weight_kg) -> list[dict]
used_by: shipping/service.py | shipping/tracking.py | shipping/rates.py
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def book_shipment(order_id: str, carrier: str):
    # Mock carrier integration
    return {'tracking': f'TRACK-{order_id[:8].upper()}', 'carrier': carrier, 'eta_days': 3}
