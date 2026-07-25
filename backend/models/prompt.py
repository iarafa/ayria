"""
Prompt: AyriaPromptConfig (alma global) e UserAlma (sub-alma individual)
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from ._base import Base, gen_uuid


# ============================================================
# 14. AYRIA_PROMPT_CONFIG (system prompt editável pelo admin — aba "ALMA")
# ============================================================
class AyriaPromptConfig(Base):
    """System prompt editável pelo admin no dashboard.

    Estrutura key-value simples (key= 'system_prompt', is_active=true).
    Quando não houver config ativo, o chat.py usa o SYSTEM_PROMPT_TEMPLATE hardcoded.
    """
    __tablename__ = "ayria_prompt_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    key = Column(String(100), unique=True, nullable=False, index=True)  # ex: 'system_prompt'
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    description = Column(Text)  # nota do admin: "versão com guardrails"
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ============================================================
# 15. USER_ALMA (sub-alma individual por usuário — 08/07/2026)
# Camada 2 da alma: modula a constituição base por user.
# Plano: 01_Memories/AYRIA_SUB_ALMA_PLANO_08072026.md
# ============================================================
class UserAlma(Base):
    """Sub-alma individual do usuário.

    Diferente de `ayria_prompt_config` (que é a constituição GLOBAL do produto),
    esta tabela guarda a alma INDIVIDUAL por user. Nascida no fim do onboarding,
    regenerável pelo admin, editável pela IA com base em sinais.
    """
    __tablename__ = "user_alma"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)  # 1, 2, 3... por user
    status = Column(String(20), nullable=False, default="draft", index=True)  # draft|active|superseded|archived

    content = Column(Text, nullable=False)  # markdown estruturado
    signals_used = Column(JSONB, nullable=False, default=dict)  # auditoria
    trigger = Column(String(50), nullable=False)  # onboarding_complete|admin_manual|periodic|preference_signal|...
    model_used = Column(String(100), nullable=False)

    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))  # null se for auto
    expires_at = Column(DateTime(timezone=True))  # draft que expira em X dias
    manual_lock = Column(JSONB, nullable=False, default=dict)  # campos travados contra regeneração

    __table_args__ = (
        UniqueConstraint('user_id', 'version', name='user_alma_user_version_uq'),
    )
