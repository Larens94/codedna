import os
import json
import logging
from core.db import execute, execute_one
from core.config import *
from flask import Blueprint, request, jsonify
from core.auth import verify_token, require_auth, require_admin

analytics_api_bp = Blueprint('analytics_api', __name__, url_prefix='/api/analytics-api')

def revenue_route():
    year = int(request.args.get('year',2025))
    month = int(request.args.get('month',1))
    payload = verify_token(request.headers.get('Authorization','').replace('Bearer ',''))
    if payload.get('role') not in ('admin','owner'): return jsonify({'error':'Forbidden'}),403
    return jsonify(monthly_revenue(year,month))

def cohort_route():
    months = int(request.args.get('months',12))
    return jsonify(cohort_retention(months))

def churn_route():
    year = int(request.args.get('year',2025))
    month = int(request.args.get('month',1))
    return jsonify({'churn_rate': churn_rate(year,month)})
