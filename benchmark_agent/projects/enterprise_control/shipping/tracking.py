import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_status(order_id: str):
    shipment = get_shipment(order_id)
    if not shipment: return {'status': 'not_shipped'}
    return {'status': shipment['status'], 'tracking': shipment['tracking_number']}
