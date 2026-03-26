"""python-api/utils/format.py — Currency, date, and string formatting utilities.

exports: format_currency(amount_cents, currency) | format_date(dt, fmt) | format_user_label(name, email) | truncate(text, max_len, suffix)
used_by: none
rules:   - All formatting functions must handle None/empty inputs gracefully without raising exceptions
- Currency formatting must support only the predefined symbol dictionary; new currencies require explicit addition to the symbols map
agent:   claude-haiku-4-5-20251001 | 2026-03-27 | initial CodeDNA annotation pass
"""

from datetime import datetime
from typing import Optional


def format_currency(amount_cents: int, currency: str = "USD") -> str:
    """
    Rules:   amount_cents must be an integer; negative values are not validated and will produce unexpected output (e.g., '-$10.00')
    """
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
    """
    Rules:   max_len must be greater than len(suffix) to avoid negative slicing; no validation exists to prevent malformed output
    """
    if not text:
        return None
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix
