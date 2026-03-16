import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def fulfill_order(order_id: str):
    order = get_order(order_id)
    if order['status'] != 'confirmed': raise InvalidStatusError()
    # TODO: decrement inventory for each item in order['items']
    update_status(order_id, 'fulfilled')
    emit('order.fulfilled', {'order_id': order_id})
    return get_order(order_id)
