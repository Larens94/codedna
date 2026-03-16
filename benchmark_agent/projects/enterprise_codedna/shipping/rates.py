# === CODEDNA:0.5 ==============================================
# FILE: shipping/rates.py
# PURPOSE: Rates logic for shipping
# CONTEXT_BUDGET: normal
# DEPENDS_ON: shipping/carriers.py :: get_rates
# EXPORTS: compare_rates(origin, destination, weight_kg) -> list[dict] | cheapest_rate(origin, destination, weight_kg) -> dict
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

def compare_rates(origin: str, destination: str, weight_kg: float):
    rates = get_rates(origin, destination, weight_kg)
    return sorted(rates, key=lambda r: r['price_cents'])
