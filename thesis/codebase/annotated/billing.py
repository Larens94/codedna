"""billing.py — Invoice lifecycle for PayTrack billing system.

exports: class Invoice
used_by: api.py → Invoice
rules:   `value` is stored in CENTS (int) — ALWAYS divide by 100 before displaying euros.
         Invoices are IMMUTABLE after state="finalized" — MUST raise ValueError before any
         mutation (set_lines, add_line, or direct attribute write) if state=="finalized".
         Penalty rate is exactly 1.5% per month (0.015 multiplier) — NEVER use a different
         rate or accept it as a parameter.
         state transitions: "draft" → "finalized" → "paid" — no other transitions valid.
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_bench | CodeDNA benchmark annotation
"""
from datetime import datetime
from typing import Optional


class Invoice:
    def __init__(self, invoice_id: str, customer_id: str, value: int,
                 state: str = "draft", lines: Optional[list] = None):
        self.invoice_id = invoice_id
        self.customer_id = customer_id
        self.value = value
        self.state = state
        self.lines = lines or []
        self.created_at = datetime.now()
        self.closed_at: Optional[datetime] = None
        self.overdue_since: Optional[datetime] = None

    def close(self):
        """Rules: Only draft invoices can be closed (finalized)."""
        if self.state != "draft":
            raise ValueError("Only draft invoices can be closed")
        self.state = "finalized"
        self.closed_at = datetime.now()

    def set_lines(self, new_lines: list):
        """Rules: MUST check state != 'finalized' — finalized invoices are immutable."""
        if self.state == "finalized":
            raise ValueError("Cannot modify a finalized invoice")
        self.lines = new_lines

    def add_line(self, desc: str, qty: int, unit: int):
        self.lines.append({"desc": desc, "qty": qty, "unit": unit})

    def get_value(self) -> int:
        """Rules: Returns value in CENTS. Caller MUST divide by 100 for euro display."""
        return self.value

    def compute_penalty(self, days_late: int) -> float:
        """Rules: Rate is exactly 0.015 (1.5%) per month. Input is days — divide by 30."""
        months_late = days_late / 30
        return self.value * months_late * 0.015

    def settle(self):
        if self.state != "finalized":
            raise ValueError("Only finalized invoices can be settled")
        self.state = "paid"
