import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def generate_and_send(year: int, month: int):
    report = full_monthly_report(year, month)
    # send to admins
