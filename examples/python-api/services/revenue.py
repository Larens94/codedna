"""revenue.py — Monthly and annual revenue aggregation from paid invoices.

exports: monthly_revenue(year, month, users) -> dict | annual_summary(year, users) -> list[dict]
         top_customers(year, month, users, limit) -> list[dict]
used_by: api/routes.py → revenue_route, annual_route, top_customers_route
rules:   get_invoices_for_period() returns ALL tenants including suspended —
         callers MUST pass a filtered users list. monthly_revenue and top_customers
         both filter by active_ids internally, but the users list must come from outside.
agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
         message: "get_invoices_for_period has no suspension filter at DB level —
                   if this moves to SQL, the WHERE clause must explicitly exclude suspended users"
"""

from datetime import datetime
from typing import Optional

from models.user import Invoice, User
from utils.format import format_currency


def get_invoices_for_period(year: int, month: int) -> list[Invoice]:
    # NOTE: returns ALL invoices including suspended users — callers must filter
    from db import session

    return (
        session.query(Invoice)
        .filter(
            Invoice.created_at >= datetime(year, month, 1),
            Invoice.paid == True,
        )
        .all()
    )


def monthly_revenue(year: int, month: int, users: list[User]) -> dict:
    active_ids = {u.id for u in users if not u.is_suspended()}
    invoices = get_invoices_for_period(year, month)
    total = sum(inv.amount_cents for inv in invoices if inv.user_id in active_ids)
    return {
        "year": year,
        "month": month,
        "total_cents": total,
        "total_formatted": format_currency(total),
        "invoice_count": len([i for i in invoices if i.user_id in active_ids]),
    }


def annual_summary(year: int, users: list[User]) -> list[dict]:
    return [monthly_revenue(year, month, users) for month in range(1, 13)]


def top_customers(year: int, month: int, users: list[User], limit: int = 10) -> list[dict]:
    active_ids = {u.id: u for u in users if not u.is_suspended()}
    invoices = get_invoices_for_period(year, month)
    totals: dict[int, int] = {}
    for inv in invoices:
        if inv.user_id in active_ids:
            totals[inv.user_id] = totals.get(inv.user_id, 0) + inv.amount_cents
    sorted_ids = sorted(totals, key=lambda uid: totals[uid], reverse=True)[:limit]
    return [{"user": active_ids[uid].display_name(), "total": format_currency(totals[uid])} for uid in sorted_ids]
