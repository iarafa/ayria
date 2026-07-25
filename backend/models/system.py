"""
System: SystemConfig, ActionType
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from ._base import Base, gen_uuid


# ============================================================
# 17. SYSTEM_CONFIG (configurações editáveis do sistema — 19/07/2026)
# Key/value store para sobrescrever variáveis do .env sem reiniciar.
# Usado para: AI_API_KEY, AI_BASE_URL, AI_MODEL, AI_PROVIDER.
# Quando chave existe no DB, sobrepõe o valor do .env em runtime.
# ============================================================
class SystemConfig(Base):
    """Config editável em runtime pelo painel admin.
    Key = nome da config (ex: 'AI_API_KEY'), value = valor persistido.
    Audit: updated_by registra QUAL admin mudou.
    """
    __tablename__ = "system_config"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text)  # o que essa config faz (pra tooltip no painel)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ============================================================
# 24. ACTION_TYPES (21/07/2026 11:18)
# Catálogo de tipos de ação com custo variável em créditos
# Decisão Rafael: 1 cr (chat simples), 2 (chat profundo), 5 (especiais)
# ============================================================
class ActionType(Base):
    __tablename__ = "action_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    slug = Column(String(50), unique=True, nullable=False, index=True)   # 'chat_simples' | 'cartomancia'
    name = Column(String(100), nullable=False)
    description = Column(Text)
    credits_cost = Column(Integer, nullable=False)                        # quanto desconta
    is_special = Column(Boolean, default=False, nullable=False)           # TRUE = ação premium
    category = Column(String(50), default="chat", nullable=False)         # chat|mystic|astrology|divination
    icon = Column(String(50))                                              # emoji ou nome de ícone
    sort_order = Column(Integer, default=0, nullable=False)
    active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
