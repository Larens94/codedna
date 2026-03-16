import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def create_shipment(order_id: str, carrier: str, tracking: str):
    return execute_one('INSERT INTO shipments (order_id, carrier, tracking_number) VALUES (%s,%s,%s) RETURNING *', (order_id, carrier, tracking))
