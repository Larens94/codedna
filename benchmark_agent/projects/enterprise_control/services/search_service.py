import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def search_products(tenant_id:str, query:str, filters:dict={}):
    return execute('SELECT * FROM products WHERE tenant_id=%s AND name ILIKE %s AND deleted_at IS NULL', (tenant_id,f'%{query}%'))

def search_orders(tenant_id:str, query:str):
    return execute('SELECT * FROM orders WHERE tenant_id=%s AND id ILIKE %s', (tenant_id,f'%{query}%'))

def search_tenants_admin(query:str):
    return execute('SELECT * FROM tenants WHERE name ILIKE %s AND deleted_at IS NULL', (f'%{query}%',))
