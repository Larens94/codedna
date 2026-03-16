"""db/redis_client.py -- Redis client for caching and queues.

Depends on: config.py :: REDIS_URL
Exports: cache_set(key, value, ttl), cache_get(key), cache_del(key)
Used by: services/auth_service.py, workers/cache_warmer.py
"""
import redis
from config import REDIS_URL

_client = None

def get_redis():
    global _client
    if _client is None:
        _client = redis.from_url(REDIS_URL)
    return _client

def cache_set(key: str, value: str, ttl: int = 300):
    get_redis().setex(key, ttl, value)

def cache_get(key: str) -> str | None:
    val = get_redis().get(key)
    return val.decode() if val else None

def cache_del(key: str):
    get_redis().delete(key)
