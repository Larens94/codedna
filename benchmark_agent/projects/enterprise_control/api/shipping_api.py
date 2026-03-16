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
