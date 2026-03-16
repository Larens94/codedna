import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def calculate_tax(amount_cents:int, country:str):
    rates = {'IT':0.22,'DE':0.19,'FR':0.20,'ES':0.21}
    return round(amount_cents * rates.get(country, 0.20))

def get_tax_report_for_period(year:int, month:int):
    return execute('SELECT country, SUM(tax_cents) FROM invoices WHERE EXTRACT(YEAR FROM created_at)=%s AND EXTRACT(MONTH FROM created_at)=%s GROUP BY country', (year,month))
