"""
Schemas do dashboard de Rate Limit + blacklist.
"""
from typing import Optional
from pydantic import BaseModel

from ._base import _List, _Dict, _Any


class RateLimitStatusResponse(BaseModel):
    """Resumo agregado para o card no dashboard."""
    ips_blocked_now: int
    ips_in_alert: int
    total_failures_24h: int
    total_blocks_24h: int
    paused: bool


class RateLimitBlockedIP(BaseModel):
    ip: str
    endpoint: str
    geo: Optional[str] = None
    failures_in_window: int
    retry_in_seconds: int
    blocked_until_epoch: float
    blocked_until_iso: str
    user_agent: Optional[str] = None
    last_email_attempted: Optional[str] = None


class RateLimitAlertIP(BaseModel):
    ip: str
    endpoint: str
    geo: Optional[str] = None
    failures_in_window: int
    user_agent: Optional[str] = None


class RateLimitEventsPage(BaseModel):
    items: _List[_Dict[str, _Any]]
    total: int


class RateLimitBlockedList(BaseModel):
    items: _List[RateLimitBlockedIP]
    total: int


class RateLimitAlertList(BaseModel):
    items: _List[RateLimitAlertIP]
    total: int


class BlacklistItem(BaseModel):
    ip: str
    reason: Optional[str] = None
    added_by: str
    added_at: str
    expires_at: Optional[str] = None


class BlacklistAddRequest(BaseModel):
    ip: str
    reason: Optional[str] = None
    expires_at: Optional[str] = None


class BlacklistResponse(BaseModel):
    items: _List[BlacklistItem]
    total: int


class RateLimitUnblockRequest(BaseModel):
    ip: str
    endpoint: Optional[str] = None  # se None, limpa tudo do IP


class RateLimitConfigResponse(BaseModel):
    login: _Dict[str, _Any]
    register: _Dict[str, _Any]
    forgot_password: _Dict[str, _Any]


class RateLimitToggleRequest(BaseModel):
    paused: bool
