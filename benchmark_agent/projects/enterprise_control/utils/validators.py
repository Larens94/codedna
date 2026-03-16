import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def validate_email(email:str):
    import re
    return bool(re.match(r'^[^@]+@[^@]+\.[^@]+$', email))

def validate_plan(plan:str):
    return plan in ('starter','growth','business','enterprise')

def validate_currency_amount(amount_cents:int):
    return isinstance(amount_cents,int) and amount_cents >= 0
