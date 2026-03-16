"""notifications/sms.py — Sms module.

deps:    core/config.py
exports: send_sms(phone, message) -> None | send_otp(phone) -> str
used_by: none
tables:  none
rules:   none
"""

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
