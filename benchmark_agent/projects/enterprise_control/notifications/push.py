import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def send_push(user_id: str, title: str, body: str):
    token = execute_one('SELECT fcm_token FROM users WHERE id=%s', (user_id,))
    if not token or not token['fcm_token']: return
    # FCM API call
