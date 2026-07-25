"""
User, UserProfile, UserAttribute
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ._base import Base, gen_uuid


# ============================================================
# 1. USERS
# ============================================================
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    avatar_url = Column(String(500))
    role = Column(String(20), default="user", index=True)  # user | admin | SUPER_ADMIN
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    # Email verification (07/07/2026)
    verification_token = Column(String(64), index=True)
    verification_token_expires_at = Column(DateTime(timezone=True))
    verification_sent_at = Column(DateTime(timezone=True))
    verified_at = Column(DateTime(timezone=True))
    # Password reset (19/07/2026 — single-use, 1h)
    password_reset_token = Column(String(64), index=True)
    password_reset_token_expires_at = Column(DateTime(timezone=True))
    password_reset_sent_at = Column(DateTime(timezone=True))
    numerology_data = Column(JSONB)
    astrology_data = Column(JSONB)
    profile_status = Column(String(50), default="pending")
    onboarding_status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))

    # BILLING / PLANOS / CRÉDITOS
    selected_plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id", ondelete="SET NULL"), index=True)
    credit_balance = Column(Integer, nullable=False, default=0)
    credit_status = Column(String(50), nullable=False, default="inactive")
    plan_selected_at = Column(DateTime(timezone=True))
    billing_status = Column(String(50), nullable=False, default="billing_not_enabled")
    billing_provider = Column(String(50))
    external_customer_id = Column(String(255))
    external_subscription_id = Column(String(255))
    next_renewal_date = Column(DateTime(timezone=True))
    credits_last_granted_at = Column(DateTime(timezone=True))

    # BLOCK (controle de acesso manual pelo admin)
    blocked_until = Column(DateTime(timezone=True))
    blocked_at = Column(DateTime(timezone=True))
    blocked_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    block_reason = Column(Text)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    documents_uploaded = relationship("KnowledgeDocument", back_populates="uploader")
    selected_plan = relationship("Plan", back_populates="users", foreign_keys=[selected_plan_id])
    credit_transactions = relationship("CreditTransaction", back_populates="user", cascade="all, delete-orphan", order_by="CreditTransaction.created_at.desc()")
    supervisor_analyses = relationship("SupervisorAnalysis", back_populates="user", cascade="all, delete-orphan")
    supervisor_alerts = relationship("SupervisorAlert", back_populates="user", cascade="all, delete-orphan", foreign_keys="SupervisorAlert.user_id")
    supervisor_daily_summaries = relationship("SupervisorDailySummary", back_populates="user", cascade="all, delete-orphan")
    spiritual_preference = relationship("SpiritualPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")


# ============================================================
# 2. USER_PROFILES (JSONB flexível)
# ============================================================
class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    attributes = Column(JSONB, default=dict)
    onboarding_completed = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")


# ============================================================
# 3b. USER_ATTRIBUTES (valores por usuário)
# ============================================================
class UserAttribute(Base):
    """Valores dos atributos preenchidos por cada usuário"""
    __tablename__ = "user_attributes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    attribute_definition_id = Column(UUID(as_uuid=True), ForeignKey("attribute_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    value = Column(JSONB, nullable=False)
    # Status do atributo (migração 007):
    # - 'answered': user respondeu, valor em `value`
    # - 'skipped': user pulou no onboarding, NÃO pergunta de novo
    # - 'pending_next_chat': user disse "responder depois", pergunta no PRÓXIMO chat
    # - 'pending_current_chat': pergunta ativa no chat atual (aguardando resposta)
    # - 'snoozed': user pediu pra adiar, lembra depois de snooze_until
    status = Column(String(20), nullable=False, default='answered')
    skipped_at = Column(DateTime(timezone=True))
    snooze_until = Column(DateTime(timezone=True))
    last_asked_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
