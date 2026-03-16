import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def compare_rates(origin: str, destination: str, weight_kg: float):
    rates = get_rates(origin, destination, weight_kg)
    return sorted(rates, key=lambda r: r['price_cents'])
