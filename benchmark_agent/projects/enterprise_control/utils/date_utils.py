import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def first_day_of_month(year:int, month:int):
    return f'{year}-{month:02d}-01'

def last_day_of_month(year:int, month:int):
    import calendar
    return f'{year}-{month:02d}-{calendar.monthrange(year,month)[1]}'

def parse_date(date_str:str):
    from datetime import datetime
    return datetime.strptime(date_str,'%Y-%m-%d').date()
