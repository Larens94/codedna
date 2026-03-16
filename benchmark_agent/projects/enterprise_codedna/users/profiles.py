"""users/profiles.py — Profiles module.

deps:    users/models.py :: get_user | users/models.py :: update_user | core/cache.py :: cache_set
exports: get_profile(user_id) -> dict | update_profile(user_id, data) -> dict | update_avatar(user_id, url) -> None
used_by: none
tables:  users(id, tenant_id, email, role, active)
rules:   none
"""

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
