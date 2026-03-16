# === CODEDNA:0.5 ==============================================
# FILE: users/service.py
# PURPOSE: Service logic for users
# CONTEXT_BUDGET: normal
# DEPENDS_ON: users/models.py | tenants/limits.py :: check_seat_limit | notifications/email.py :: send_welcome
# EXPORTS: invite_user(tenant_id, email, name, role) -> dict | deactivate(user_id) -> None | change_role(user_id, new_role) -> None
# REQUIRED_BY: none
# DB_TABLES: users (id, tenant_id, email, name, role, active, last_login) | tenants (id, name, plan, owner_email, suspended_at, deleted_at)
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def invite_user(tenant_id: str, email: str, name: str, role: str = 'member'):
    if not check_seat_limit(tenant_id): raise SeatLimitError('Seat limit reached')
    user = create_user(tenant_id, email, name, role)
    send_welcome(email, name)
    return user
