"""users.py — User account management for PayTrack.

exports: class User
used_by: api.py → User
rules:   NEVER hard-delete users — soft-delete by setting deleted_at = datetime.now().
         is_suspended() checks suspension_end > datetime.now() — NOT a boolean flag.
         get_all() returns all non-deleted users INCLUDING suspended ones — callers MUST
         filter with is_suspended() before showing active users or sending notifications.
         Password verification MUST use bcrypt.checkpw — never compare plain text.
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_bench | initial CodeDNA annotation
"""
from datetime import datetime
from typing import Optional, List


class User:
    _all: List["User"] = []

    def __init__(self, user_id: str, email: str, password_hash: str,
                 role: str = "user"):
        self.user_id = user_id
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.deleted_at: Optional[datetime] = None
        self.suspension_end: Optional[datetime] = None
        self.created_at = datetime.now()
        User._all.append(self)

    def is_suspended(self) -> bool:
        """Rules: Checks suspension_end > now(). Returns False if suspension_end is None."""
        if self.suspension_end is None:
            return False
        return self.suspension_end > datetime.now()

    def remove(self):
        """Rules: SOFT DELETE ONLY — sets deleted_at. Never removes from _all list."""
        self.deleted_at = datetime.now()

    def suspend(self, until: datetime):
        self.suspension_end = until

    @classmethod
    def get_all(cls) -> List["User"]:
        """Rules: Returns ALL non-deleted users INCLUDING suspended. Caller MUST filter is_suspended()."""
        return [u for u in cls._all if u.deleted_at is None]

    @classmethod
    def get_by_id(cls, user_id: str) -> Optional["User"]:
        for u in cls._all:
            if u.user_id == user_id and u.deleted_at is None:
                return u
        return None

    def check_password(self, plain: str) -> bool:
        """Rules: MUST use bcrypt.checkpw — never compare plain text to hash."""
        import bcrypt
        return bcrypt.checkpw(plain.encode(), self.password_hash.encode())

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "role": self.role,
            "is_suspended": self.is_suspended(),
        }
