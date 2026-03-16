# === CODEDNA:0.5 ==============================================
# FILE: utils/crypto.py
# PURPOSE: Crypto logic for utils
# CONTEXT_BUDGET: minimal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: hash_password() -> str | verify_password() -> bool | generate_token() -> str
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

def hash_password(password:str):
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password:str, hash_str:str):
    import bcrypt
    return bcrypt.checkpw(password.encode(), hash_str.encode())

def generate_token(length:int=32):
    import secrets
    return secrets.token_urlsafe(length)
