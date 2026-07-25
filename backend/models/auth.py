"""
Auth: LoginLockout (anti brute-force progressivo)
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from ._base import Base


# ============================================================
# 22/07 22:50 — LOGIN LOCKOUT (anti brute-force progressivo)
# Migration: 020_login_lockout.sql
# ============================================================
class LoginLockout(Base):
    """
    Bloqueio progressivo de tentativas de login.
    3 erros → 15min, 4 → 30min, 5 → 60min, 6 → 24h, 7+ → TOTAL (admin only).
    Identificador pode ser email OU IP (fallback).
    """
    __tablename__ = "login_lockouts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identifier = Column(String(255), nullable=False)
    identifier_type = Column(String(20), nullable=False)  # 'email' | 'ip'
    failed_attempts = Column(Integer, nullable=False, default=0)
    first_failed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_failed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    locked_until = Column(DateTime(timezone=True))
    lockout_level = Column(Integer, nullable=False, default=0)  # 0=livre, 5=TOTAL
    unlocked_by = Column(String(255))
    unlocked_at = Column(DateTime(timezone=True))
    unlock_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('identifier', 'identifier_type', name='uq_login_lockouts_identifier'),
        Index('idx_login_lockouts_locked_until', 'locked_until', postgresql_where=Column('locked_until').is_not(None)),
    )
