# === CODEDNA:0.5 ==============================================
# FILE: users/profiles.py
# PURPOSE: Profiles logic for users
# CONTEXT_BUDGET: normal
# DEPENDS_ON: users/models.py :: get_user | users/models.py :: update_user | core/cache.py :: cache_set
# EXPORTS: get_profile(user_id) -> dict | update_profile(user_id, data) -> dict | update_avatar(user_id, url) -> None
# REQUIRED_BY: none
# DB_TABLES: users (id, tenant_id, email, name, role, active, last_login)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

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
