import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def can_edit_product(user_id: str):
    user = get_user(user_id)
    return user['role'] in ('admin', 'owner', 'member')

def can_manage_users(user_id: str):
    user = get_user(user_id)
    return user['role'] in ('admin', 'owner')
