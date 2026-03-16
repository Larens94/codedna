# === CODEDNA:0.5 ==============================================
# FILE: api/reports.py
# PURPOSE: Reports logic for api
# CONTEXT_BUDGET: normal
# DEPENDS_ON: analytics/reports.py :: full_monthly_report | core/auth.py :: require_admin
# EXPORTS: reports_bp (Flask Blueprint)
# REQUIRED_BY: app.py
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

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

def monthly_report_route():
    year = int(request.args.get('year', 2025))
    month = int(request.args.get('month', 1))
    report = full_monthly_report(year, month)
    return jsonify(report)
