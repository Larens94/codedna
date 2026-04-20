"""python-api/services/revenue.py — Monthly and annual revenue aggregation from paid invoices.

exports: get_invoices_for_period(year, month) | monthly_revenue(year, month, users) | annual_summary(year, users) | top_customers(year, month, users, limit)
used_by: api/routes.py → annual_summary, monthly_revenue, top_customers
rules:   - All functions must filter users through `is_suspended()` before processing revenue data; never operate on raw user lists
- Database session access is restricted to `get_invoices_for_period()`; other functions must receive pre-queried data as parameters
agent:   claude-haiku-4-5-20251001 | 2026-03-27 | initial CodeDNA annotation pass
message: 
"""

from datetime import datetime
from typing import Optional

from models.user import Invoice, User
from utils.format import format_currency


def get_invoices_for_period(year: int, month: int) -> list[Invoice]:
    # NOTE: returns ALL invoices including suspended users — callers must filter
    """
    Rules:   Returns ALL invoices including suspended users; caller must filter by user status. Only filters for paid=True invoices; unpaid invoices excluded.
    """
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
    """
    Rules:   Requires users list passed in; if user is deleted after invoice creation, KeyError will occur on active_ids[uid] lookup.
    """
    active_ids = {u.id: u for u in users if not u.is_suspended()}
    invoices = get_invoices_for_period(year, month)
    totals: dict[int, int] = {}
    for inv in invoices:
        if inv.user_id in active_ids:
            totals[inv.user_id] = totals.get(inv.user_id, 0) + inv.amount_cents
    sorted_ids = sorted(totals, key=lambda uid: totals[uid], reverse=True)[:limit]
    return [{"user": active_ids[uid].display_name(), "total": format_currency(totals[uid])} for uid in sorted_ids]
