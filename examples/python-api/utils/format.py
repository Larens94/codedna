"""format.py — Currency, date, and string formatting utilities.

exports: format_currency(amount_cents, currency) -> str | format_date(dt, fmt) -> str
         format_user_label(name, email) -> str | truncate(text, max_len, suffix) -> Optional[str]
used_by: services/revenue.py → monthly_revenue, top_customers | api/routes.py → revenue_route
rules:   format_currency expects amount in cents (int), not dollars —
         divide by 100 internally. Never pass float dollars directly.
agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
"""

from datetime import datetime
from typing import Optional


def format_currency(amount_cents: int, currency: str = "USD") -> str:
    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, currency + " ")
    return f"{symbol}{amount_cents / 100:.2f}"


def format_date(dt: datetime, fmt: str = "%Y-%m-%d") -> str:
    return dt.strftime(fmt)


def format_user_label(name: str, email: str) -> str:
    clean = name.strip()
    if clean:
        return f"{clean} <{email}>"
    return email


def truncate(text: str, max_len: int = 80, suffix: str = "...") -> Optional[str]:
    if not text:
        return None
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix
