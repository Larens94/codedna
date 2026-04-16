from datetime import datetime
from typing import Optional, List


S1 = 1
S2 = 2
S3 = 3
S4 = 4


class Order:
    _store: List["Order"] = []

    def __init__(self, oid: str, cid: str):
        self.oid = oid
        self.cid = cid
        self.s = S1
        self.lines: List[dict] = []
        self.ts = datetime.now()
        Order._store.append(self)

    def append_line(self, pid: str, qty: int, price: int):
        if self.s != S1:
            raise ValueError("Cannot modify a non-pending order")
        self.lines.append({"pid": pid, "qty": qty, "price": price})

    def void(self):
        if self.s != S1:
            raise ValueError("Only S1 orders can be voided")
        self.s = S4

    def next_state(self):
        if self.s == S1:
            self.s = S2
        elif self.s == S2:
            self.s = S3
        else:
            raise ValueError("Cannot advance from current state")

    def total(self) -> int:
        return sum(l["qty"] * l["price"] for l in self.lines)

    @classmethod
    def all(cls) -> List["Order"]:
        return list(cls._store)

    @classmethod
    def by_state(cls, state: int) -> List["Order"]:
        return [o for o in cls._store if o.s == state]
