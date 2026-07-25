"""
CreditTransaction, AIUsageLog
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ._base import Base, gen_uuid


# ============================================================
# 10. CREDIT_TRANSACTIONS (auditoria de movimentação de créditos)
# ============================================================
class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # grant_initial_plan|usage_chat_message|bonus_manual|adjustment_manual|recharge_future|refund_future
    amount = Column(Integer, nullable=False)  # positivo=grant, negativo=uso
    balance_before = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    reference_type = Column(String(50))
    reference_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="credit_transactions")


# ============================================================
# 25. AI_USAGE_LOG (21/07/2026 11:18)
# Rastreamento de tokens e custo de cada chamada de IA
# Usado pra dashboard admin + billing reconciliation
# ============================================================
class AIUsageLog(Base):
    __tablename__ = "ai_usage_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action_type_id = Column(UUID(as_uuid=True), ForeignKey("action_types.id", ondelete="SET NULL"), index=True)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="SET SET NULL"), index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"))

    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)

    cost_input_usd = Column(Numeric(12, 6), default=0, nullable=False)
    cost_output_usd = Column(Numeric(12, 6), default=0, nullable=False)
    cost_total_usd = Column(Numeric(12, 6), default=0, nullable=False)

    response_ms = Column(Integer)
    status = Column(String(20), default="success", nullable=False, index=True)  # success|error|rate_limited
    error_message = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", backref="ai_usage_logs")
    action_type = relationship("ActionType")
