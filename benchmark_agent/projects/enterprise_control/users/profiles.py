import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def get_profile(user_id: str):
    cached = cache_get(f'profile:{user_id}')
    if cached: return json.loads(cached)
    user = get_user(user_id)
    cache_set(f'profile:{user_id}', json.dumps(user), ttl=600)
    return user
