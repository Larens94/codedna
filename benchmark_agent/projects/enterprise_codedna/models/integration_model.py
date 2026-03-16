"""models/integration_model.py — Integration Model module.

deps:    core/db.py :: execute
exports: get_integrations() -> list[dict] | list_active_integrations() -> list[dict] | create_integration() -> dict
used_by: none
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_integrations(tenant_id:str):
    return execute('SELECT * FROM integrations WHERE tenant_id=%s AND active=TRUE', (tenant_id,))

def list_active_integrations(tenant_id:str):
    return execute('SELECT * FROM integrations WHERE tenant_id=%s AND suspended_at IS NULL', (tenant_id,))

def create_integration(tenant_id:str, provider:str, config:dict):
    return execute_one('INSERT INTO integrations (tenant_id,provider,config) VALUES (%s,%s,%s::jsonb) RETURNING *', (tenant_id,provider,str(config)))
