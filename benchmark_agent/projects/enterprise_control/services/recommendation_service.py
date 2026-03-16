import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_recommended_products(tenant_id:str, user_id:str, limit:int=10):
    return execute('SELECT p.* FROM products p JOIN order_items oi ON p.id=oi.product_id WHERE oi.tenant_id=%s AND p.deleted_at IS NULL GROUP BY p.id ORDER BY COUNT(*) DESC LIMIT %s', (tenant_id,limit))

def get_trending_for_period(year:int, month:int, limit:int=5):
    return execute('SELECT product_id, COUNT(*) as orders FROM order_items WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s GROUP BY product_id ORDER BY orders DESC LIMIT %s', (year,month,limit))
