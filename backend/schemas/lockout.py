"""
Schemas do LoginLockout (admin) — 22/07/2026.
"""
from typing import Optional
from pydantic import BaseModel

from ._base import datetime


class LoginLockoutInfo(BaseModel):
    identifier: str
    identifier_type: str  # 'email' | 'ip'
    failed_attempts: int
    locked_until: Optional[datetime] = None
    lockout_level: int
    is_locked: bool
    label: str
    last_failed_at: datetime
    unlocked_by: Optional[str] = None
    unlocked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoginLockoutUnlockRequest(BaseModel):
    identifier: str
    identifier_type: str = "email"
    reason: Optional[str] = None
