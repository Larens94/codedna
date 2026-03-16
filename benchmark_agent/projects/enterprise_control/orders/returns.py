import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def initiate_return(order_id: str, items: list, reason: str):
    order = get_order(order_id)
    if order['status'] != 'fulfilled': raise InvalidStatusError()
    return execute_one('INSERT INTO returns (order_id, items, reason, status) VALUES (%s,%s,%s,%s) RETURNING *', (order_id, json.dumps(items), reason, 'pending'))
