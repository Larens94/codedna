import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def login(email: str, password: str):
    user = get_user_by_email(email)
    if not user or not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        raise ValueError('Invalid credentials')
    token = sign_token(user['id'], user['role'], user['tenant_id'])
    return {'token': token, 'user': user}
