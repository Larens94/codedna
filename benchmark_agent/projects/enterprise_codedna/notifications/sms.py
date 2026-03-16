# === CODEDNA:0.5 ==============================================
# FILE: notifications/sms.py
# PURPOSE: Sms logic for notifications
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/config.py
# EXPORTS: send_sms(phone, message) -> None | send_otp(phone) -> str
# REQUIRED_BY: none
# DB_TABLES: none
# AGENT_RULES: none
# LAST_MODIFIED: initial generation
# ==============================================================

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def send_otp(phone: str):
    otp = str(random.randint(100000, 999999))
    send_sms(phone, f'Your OTP: {otp}')
    cache_set(f'otp:{phone}', otp, ttl=300)
    return otp
