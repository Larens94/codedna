import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_catalog(tenant_id: str, filters: dict = {}):
    key = f'catalog:{tenant_id}'
    cached = cache_get(key)
    if cached and not filters: return json.loads(cached)
    products = list_products(tenant_id, filters)
    if not filters: cache_set(key, json.dumps(products), ttl=120)
    return products
