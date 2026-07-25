"""
Supervisor: SupervisorAnalysis, SupervisorAlert, SupervisorDailySummary, UserSupervisorNote
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, Date, ForeignKey, SmallInteger, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ._base import Base, gen_uuid


# ============================================================
# 11. SUPERVISOR_ANALYSIS (classificação de risco por mensagem)
# ============================================================
class SupervisorAnalysis(Base):
    __tablename__ = "supervisor_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)

    level = Column(String(20), nullable=False, index=True)  # NORMAL | ATENCAO | URGENCIA
    risk_sublevel = Column(SmallInteger)  # 1=N1(suicídio), 2=N2(crime/violência), 3=N3(vício)
    score = Column(Numeric(4, 3), nullable=False, default=0.0)
    reason = Column(Text)
    recommended_action = Column(Text)
    signals = Column(JSONB, default=list)  # list[str] de sinais detectados
    context_used = Column(JSONB, default=dict)  # contexto adicional (numerologia, etc)

    model_used = Column(String(50), default="MiniMax-M3")
    analysis_duration_ms = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="supervisor_analyses")
    chat = relationship("Chat", back_populates="supervisor_analyses")
    message = relationship("Message", back_populates="supervisor_analyses")
    alerts = relationship("SupervisorAlert", back_populates="analysis", cascade="all, delete-orphan")


# ============================================================
# 12. SUPERVISOR_ALERTS (alertas críticos notificados ao admin)
# ============================================================
class SupervisorAlert(Base):
    __tablename__ = "supervisor_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("supervisor_analysis.id", ondelete="SET NULL"))

    level = Column(String(20), nullable=False, index=True)  # ATENCAO | URGENCIA
    status = Column(String(20), nullable=False, default="open", index=True)  # open|acknowledged|resolved|dismissed
    title = Column(Text, nullable=False)
    message = Column(Text)
    message_excerpt = Column(Text)

    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    resolved_at = Column(DateTime(timezone=True))
    resolution_notes = Column(Text)

    occurrences = Column(Integer, default=1)
    last_occurrence_at = Column(DateTime(timezone=True), server_default=func.now())

    # TRUE = análise veio da IA, FALSE = só do pré-check regex, NULL = legado
    ia_confirmed = Column(Boolean, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="supervisor_alerts", foreign_keys=[user_id])
    analysis = relationship("SupervisorAnalysis", back_populates="alerts")


# ============================================================
# 13. SUPERVISOR_DAILY_SUMMARY (resumo diário por user)
# ============================================================
class SupervisorDailySummary(Base):
    __tablename__ = "supervisor_daily_summary"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    summary_date = Column(Date, nullable=False, index=True)

    total_messages = Column(Integer, default=0)
    normal_count = Column(Integer, default=0)
    atencao_count = Column(Integer, default=0)
    urgencia_count = Column(Integer, default=0)
    current_level = Column(String(20), default="NORMAL")
    max_score = Column(Numeric(4, 3), default=0.0)

    user = relationship("User", back_populates="supervisor_daily_summaries")


# ============================================================
# 16. USER_SUPERVISOR_NOTES (notas/análises manuais do admin sobre um user)
# ============================================================
class UserSupervisorNote(Base):
    """Notas/análises manuais que o admin grava após conversar com a IA
    trancada em um user específico. Diferente de `SupervisorAnalysis`
    (automático, 1 por msg), esta é manual e 1 por sessão de análise.
    """
    __tablename__ = "user_supervisor_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(20), nullable=False, default="analysis")  # analysis|observation|action
    title = Column(Text)
    content = Column(Text, nullable=False)
    conversation = Column(JSONB, nullable=False, default=list)  # histórico do chat
    model_used = Column(String(100), nullable=False)
    signals_used = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
