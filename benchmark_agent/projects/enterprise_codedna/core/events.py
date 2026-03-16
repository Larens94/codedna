# === CODEDNA:0.5 ==============================================
# FILE: core/events.py
# PURPOSE: Events logic for core
# CONTEXT_BUDGET: always
# DEPENDS_ON: core/cache.py | core/db.py
# EXPORTS: emit(event_name, payload) -> None | subscribe(event_name, handler) -> None
# REQUIRED_BY: products/service.py | orders/fulfillment.py | payments/webhooks.py
# DB_TABLES: none
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

_registry: dict = {}

def emit(event_name: str, payload: dict):
    _handlers = _registry.get(event_name, [])
    for h in _handlers: h(payload)

def subscribe(event_name: str, handler):
    _registry.setdefault(event_name, []).append(handler)
