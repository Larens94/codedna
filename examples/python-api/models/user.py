"""python-api/models/user.py — User and Invoice dataclasses for the revenue domain.

exports: class User | class Invoice
used_by: api/routes.py → User
         services/revenue.py → Invoice, User
rules:   User.display_name() depends on self.name and self.email existing as non-null attributes. Invoice.amount_formatted() assumes self.amount_cents is always a numeric type. Both classes must maintain these attributes or their respective methods will raise exceptions.
agent:   claude-haiku-4-5-20251001 | 2026-03-27 | initial CodeDNA annotation pass
message: 
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: int
    email: str
    name: str
    is_active: bool = True
    suspended_at: Optional[datetime] = None

    def is_suspended(self) -> bool:
        return self.suspended_at is not None

    def display_name(self) -> str:
        """
        Rules:   Assumes email is valid format with '@' present; will raise IndexError if email lacks domain.
        """
        return self.name.strip() or self.email.split("@")[0]


@dataclass
class Invoice:
    id: int
    user_id: int
    amount_cents: int
    paid: bool
    created_at: datetime

    def amount_formatted(self) -> str:
        """
        Rules:   amount_cents must be an integer; decimal values will produce incorrect formatting.
        """
        return f"${self.amount_cents / 100:.2f}"
