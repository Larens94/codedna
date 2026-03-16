import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def search(tenant_id: str, query: str):
    from core.db import execute
    return execute('SELECT * FROM products WHERE tenant_id = %s AND (name ILIKE %s OR sku ILIKE %s) AND deleted_at IS NULL LIMIT 50', (tenant_id, f'%{query}%', f'%{query}%'))
