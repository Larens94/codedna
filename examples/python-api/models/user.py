"""user.py — User and Invoice dataclasses for the revenue domain.

exports: class User | class Invoice
used_by: services/revenue.py → monthly_revenue, top_customers | api/routes.py → revenue_route
rules:   User.is_suspended() is the single source of truth for suspension state —
         never check suspendedAt directly; always call is_suspended().
agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
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
        return self.name.strip() or self.email.split("@")[0]


@dataclass
class Invoice:
    id: int
    user_id: int
    amount_cents: int
    paid: bool
    created_at: datetime

    def amount_formatted(self) -> str:
        return f"${self.amount_cents / 100:.2f}"
