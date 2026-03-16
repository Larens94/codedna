import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def sync_all():
    tenants = execute('SELECT id FROM tenants WHERE suspended_at IS NULL')
    for t in tenants: sync_tenant(t['id'])
