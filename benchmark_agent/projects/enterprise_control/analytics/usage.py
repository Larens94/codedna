import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_tenant_usage(tenant_id: str):
    orders = list_orders(tenant_id, status=None)
    return {
        'tenant_id': tenant_id,
        'order_count': len(orders),
        'product_count': count_products_by_tenant(tenant_id),
        'user_count': count_users_by_tenant(tenant_id),
    }
