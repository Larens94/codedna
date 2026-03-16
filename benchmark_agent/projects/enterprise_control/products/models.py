import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_product(product_id: str):
    return execute_one('SELECT * FROM products WHERE id = %s AND deleted_at IS NULL', (product_id,))

def list_products(tenant_id: str, filters: dict = {}):
    sql = 'SELECT * FROM products WHERE tenant_id = %s AND deleted_at IS NULL'
    params = [tenant_id]
    if filters.get('category'): sql += ' AND category = %s'; params.append(filters['category'])
    return execute(sql, tuple(params))

def count_products_by_tenant(tenant_id: str):
    row = execute_one('SELECT COUNT(*) as n FROM products WHERE tenant_id = %s AND deleted_at IS NULL', (tenant_id,))
    return row['n'] if row else 0
