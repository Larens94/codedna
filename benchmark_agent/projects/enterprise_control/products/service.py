import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def create(tenant_id: str, data: dict):
    if not check_product_limit(tenant_id): raise ProductLimitError('Product limit reached')
    product = create_product(tenant_id, data)
    emit('product.updated', {'tenant_id': tenant_id, 'product_id': product['id']})
    return product
