from datetime import datetime
from typing import Optional, List


class User:
    _registry: List["User"] = []

    def __init__(self, uid: str, email: str, pwd_hash: str, role: str = "user"):
        self.uid = uid
        self.email = email
        self.pwd_hash = pwd_hash
        self.role = role
        self.removed_at: Optional[datetime] = None
        self.blocked_until: Optional[datetime] = None
        self.created_at = datetime.now()
        User._registry.append(self)

    def is_blocked(self) -> bool:
        if self.blocked_until is None:
            return False
        return self.blocked_until > datetime.now()

    def deactivate(self):
        self.removed_at = datetime.now()

    def block(self, until: datetime):
        self.blocked_until = until

    @classmethod
    def fetch_all(cls) -> List["User"]:
        return [u for u in cls._registry if u.removed_at is None]

    @classmethod
    def find(cls, uid: str) -> Optional["User"]:
        for u in cls._registry:
            if u.uid == uid and u.removed_at is None:
                return u
        return None

    def verify(self, plain: str) -> bool:
        import bcrypt
        return bcrypt.checkpw(plain.encode(), self.pwd_hash.encode())
