"""
Onboarding: OnboardingConfig, ChatQuestionSkip, SpiritualPreference
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.dialects.postgresql import ARRAY as PgArray
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ._base import Base, gen_uuid


# ============================================================
# 4. ONBOARDING_CONFIG (fluxo dinâmico)
# ============================================================
class OnboardingConfig(Base):
    """Configuração dinâmica do onboarding"""
    __tablename__ = "onboarding_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    step = Column(Integer, nullable=False)
    attribute_code = Column(String(100))  # opcional
    question_text = Column(Text, nullable=False)
    helper_text = Column(Text)
    question_type = Column(String(50), nullable=False)
    options = Column(JSONB)
    conditional_show = Column(JSONB)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# SISTEMA 2 v3 — Perguntas puladas POR CHAT (reset ao criar novo chat)
# ============================================================
class ChatQuestionSkip(Base):
    __tablename__ = "chat_question_skip"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    attribute_code = Column(String(100), nullable=False)
    skipped_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('chat_id', 'attribute_code', name='chat_question_skip_chat_code_uq'),
    )


# ============================================================
# SISTEMA 5 — Preferência espiritual/religiosa do user
# (1:1 com user; NULL = não respondeu)
# ============================================================
class SpiritualPreference(Base):
    __tablename__ = "spiritual_preferences"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    religion = Column(String(100), nullable=False)  # ex: 'cristao_catolico'
    custom_label = Column(String(255))               # preenchido se religion='outro'
    custom_tags = Column(PgArray(Text), default=list) # tags extras
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="spiritual_preference")
