import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

PLAN_LIMITS = {
    'starter':    {'seats': 5,   'products': 100},
    'growth':     {'seats': 25,  'products': 1000},
    'business':   {'seats': 100, 'products': 10000},
    'enterprise': {'seats': 500, 'products': 999999},
}

def check_seat_limit(tenant_id: str):
    tenant = get_tenant(tenant_id)
    plan = tenant['plan']
    limit = PLAN_LIMITS[plan]['seats']
    current = count_users_by_tenant(tenant_id)
    return current < limit
