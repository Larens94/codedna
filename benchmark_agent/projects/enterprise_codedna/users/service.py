"""users/service.py — Service module.

deps:    users/models.py | tenants/limits.py :: check_seat_limit | notifications/email.py :: send_welcome
exports: invite_user(tenant_id, email, name, role) -> dict | deactivate(user_id) -> None | change_role(user_id, new_role) -> None
used_by: none
tables:  users(id, tenant_id, email, role, active) | tenants(id, plan, suspended_at, deleted_at)
rules:   none
"""

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
