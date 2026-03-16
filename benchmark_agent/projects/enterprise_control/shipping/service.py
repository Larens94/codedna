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
