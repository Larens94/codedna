"""middleware/cors_handler.py — Cors Handler module.

deps:    core/db.py :: execute
exports: add_cors_headers() -> object
used_by: none
tables:  none
rules:   none
"""

import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def add_cors_headers(response:object):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response
