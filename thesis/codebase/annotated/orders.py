"""orders.py — Order lifecycle management for PayTrack.

exports: STATUS_PENDING | STATUS_PROCESSING | STATUS_SHIPPED | STATUS_CANCELLED | class Order
used_by: api.py → Order, STATUS_PENDING, STATUS_SHIPPED
rules:   Status codes are INTEGERS: 1=pending, 2=processing, 3=shipped, 4=cancelled.
         Use the STATUS_* constants — NEVER compare against strings like "shipped".
         Orders can only be cancelled when status == STATUS_PENDING (1). Check before cancel.
         Order items are APPEND-ONLY after placement — never remove items from a placed order.
         get_total() returns value in CENTS — same as billing.py amount convention.
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_bench | initial CodeDNA annotation
"""
from datetime import datetime
from typing import Optional, List


STATUS_PENDING = 1
STATUS_PROCESSING = 2
STATUS_SHIPPED = 3
STATUS_CANCELLED = 4


class Order:
    _all: List["Order"] = []

    def __init__(self, order_id: str, customer_id: str):
        self.order_id = order_id
        self.customer_id = customer_id
        self.status = STATUS_PENDING
        self.items: List[dict] = []
        self.created_at = datetime.now()
        Order._all.append(self)

    def add_item(self, product_id: str, quantity: int, unit_price: int):
        """Rules: Only allowed when status == STATUS_PENDING."""
        if self.status != STATUS_PENDING:
            raise ValueError("Cannot add items to a non-pending order")
        self.items.append({
            "product_id": product_id,
            "quantity": quantity,
            "unit_price": unit_price
        })

    def cancel(self):
        """Rules: MUST check status == STATUS_PENDING before cancelling. Raises for any other status."""
        if self.status != STATUS_PENDING:
            raise ValueError("Only pending orders can be cancelled")
        self.status = STATUS_CANCELLED

    def advance(self):
        if self.status == STATUS_PENDING:
            self.status = STATUS_PROCESSING
        elif self.status == STATUS_PROCESSING:
            self.status = STATUS_SHIPPED
        else:
            raise ValueError("Cannot advance order from current status")

    def get_total(self) -> int:
        """Rules: Returns total in CENTS (sum of quantity * unit_price). Divide by 100 for display."""
        return sum(i["quantity"] * i["unit_price"] for i in self.items)

    @classmethod
    def get_all(cls) -> List["Order"]:
        return list(cls._all)

    @classmethod
    def get_by_status(cls, status: int) -> List["Order"]:
        """Rules: status parameter must be an integer STATUS_* constant, not a string."""
        return [o for o in cls._all if o.status == status]

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "status": self.status,
            "items": self.items,
            "total": self.get_total(),
        }
