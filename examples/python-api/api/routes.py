"""routes.py — Flask Blueprint for revenue API endpoints.

exports: bp (Blueprint) — routes: GET /<year>/<month>, GET /<year>/summary, GET /<year>/<month>/top
used_by: none
rules:   all routes call _get_active_users() which returns only is_active==True users —
         suspended users are excluded upstream in services/revenue.py, not here.
         limit on /top is capped at 100 to prevent abuse.
agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
"""
from flask import Blueprint, jsonify, request

from models.user import User
from services.revenue import annual_summary, monthly_revenue, top_customers
from utils.format import format_date

bp = Blueprint("revenue", __name__, url_prefix="/api/revenue")


def _get_active_users() -> list[User]:
    from db import session
    return session.query(User).filter(User.is_active == True).all()


@bp.route("/<int:year>/<int:month>")
def revenue_route(year: int, month: int):
    if not (1 <= month <= 12):
        return jsonify({"error": "month must be 1-12"}), 400
    users = _get_active_users()
    data = monthly_revenue(year, month, users)
    return jsonify(data)


@bp.route("/<int:year>/summary")
def annual_route(year: int):
    users = _get_active_users()
    data = annual_summary(year, users)
    return jsonify(data)


@bp.route("/<int:year>/<int:month>/top")
def top_customers_route(year: int, month: int):
    limit = min(int(request.args.get("limit", 10)), 100)
    users = _get_active_users()
    data = top_customers(year, month, users, limit=limit)
    return jsonify(data)
