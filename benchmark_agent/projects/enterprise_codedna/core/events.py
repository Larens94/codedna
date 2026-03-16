"""core/events.py — Events module.

deps:    core/cache.py | core/db.py
exports: emit(event_name, payload) -> None | subscribe(event_name, handler) -> None
used_by: products/service.py | orders/fulfillment.py | payments/webhooks.py
tables:  none
rules:   none
"""

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
