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
