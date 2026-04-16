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
        if self.state != "draft":
            raise ValueError("Only draft invoices can be closed")
        self.state = "finalized"
        self.closed_at = datetime.now()

    def set_lines(self, new_lines: list):
        self.lines = new_lines

    def add_line(self, desc: str, qty: int, unit: int):
        self.lines.append({"desc": desc, "qty": qty, "unit": unit})

    def get_value(self) -> int:
        return self.value

    def compute_penalty(self, days_late: int) -> float:
        months_late = days_late / 30
        return self.value * months_late * 0.015

    def settle(self):
        if self.state != "finalized":
            raise ValueError("Only finalized invoices can be settled")
        self.state = "paid"
