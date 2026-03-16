# === CODEDNA:0.5 ==============================================
# FILE: api/shipping_api.py
# PURPOSE: Shipping Api logic for api
# CONTEXT_BUDGET: normal
# DEPENDS_ON: core/db.py :: execute
# EXPORTS: ship_route() -> None | tracking_route() -> None | rates_route() -> None
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
from flask import Blueprint, request, jsonify
from core.auth import verify_token, require_auth, require_admin

shipping_api_bp = Blueprint('shipping_api', __name__, url_prefix='/api/shipping-api')

def ship_route():
    data = request.json
    shipment = ship_order(data['order_id'], data['carrier'])
    return jsonify(shipment),201

def tracking_route():
    order_id = request.view_args['order_id']
    return jsonify(get_status(order_id))

def rates_route():
    data = request.json
    rates = compare_rates(data['origin'],data['destination'],data['weight_kg'])
    return jsonify(rates)
