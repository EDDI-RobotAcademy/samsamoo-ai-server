from typing import Optional
from datetime import datetime

class Account:
    def __init__(self, email: str, nickname: str, role: str = "USER"):
        self.id: Optional[int] = None
        self.email = email
        self.nickname = nickname
        self.role = role
        self.created_at: datetime = datetime.utcnow()
        self.updated_at: datetime = datetime.utcnow()

    def update_nickname(self, nickname: str):
        self.nickname = nickname
        self.updated_at = datetime.utcnow()
