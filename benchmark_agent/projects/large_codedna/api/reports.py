"""api/reports.py -- Revenue report API endpoints.

Depends on: reports/monthly_revenue.py :: generate_monthly_report(), generate_annual_summary(),
            api/auth.py :: require_admin
Exports: reports_bp (Flask Blueprint)
Used by: app.py :: create_app()
"""
from flask import Blueprint, request, jsonify
from reports.monthly_revenue import generate_monthly_report, generate_annual_summary
from api.auth import require_admin

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")

@reports_bp.route("/monthly", methods=["GET"])
@require_admin
def monthly():
    year = int(request.args.get("year", 2025))
    month = int(request.args.get("month", 1))
    report = generate_monthly_report(year, month)
    return jsonify(report)

@reports_bp.route("/annual", methods=["GET"])
@require_admin
def annual():
    year = int(request.args.get("year", 2025))
    summary = generate_annual_summary(year)
    return jsonify(summary)
