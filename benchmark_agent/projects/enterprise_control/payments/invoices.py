import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def create_invoice(order_id: str, tenant_id: str, total_cents: int):
    # total_cents already includes tax from orders/checkout.py
    return create_invoice_record(order_id, tenant_id, total_cents, 'outstanding')
