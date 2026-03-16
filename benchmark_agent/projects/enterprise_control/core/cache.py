import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

import redis as _redis
_client = None
def _r():
    global _client
    if _client is None: _client = _redis.from_url(REDIS_URL)
    return _client

def cache_get(key: str):
    val = _r().get(key)
    return val.decode() if val else None

def cache_set(key: str, value: str, ttl: int = 300):
    _r().setex(key, ttl, value)

def cache_del(key: str):
    _r().delete(key)

def cache_invalidate_prefix(prefix: str):
    keys = _r().keys(f'{prefix}:*')
    if keys: _r().delete(*keys)
