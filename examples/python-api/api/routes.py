"""python-api/api/routes.py — Flask Blueprint for revenue API endpoints.

exports: revenue_route(year, month) | annual_route(year) | top_customers_route(year, month)
used_by: none
rules:   All route functions must validate input parameters (year/month ranges) before querying the database, and limit result sets to prevent performance degradation. The module depends on a `db.session` object from an external `db` module for all data access.
agent:   claude-haiku-4-5-20251001 | 2026-03-27 | initial CodeDNA annotation pass
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
    """
    Rules:   limit parameter is capped at 100 max; silently truncates higher values without warning
    """
    limit = min(int(request.args.get("limit", 10)), 100)
    users = _get_active_users()
    data = top_customers(year, month, users, limit=limit)
    return jsonify(data)
