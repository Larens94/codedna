import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def cleanup_expired_carts():
    n = execute('DELETE FROM sessions WHERE expires_at < NOW()')
    return len(n)
