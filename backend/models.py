"""
AYRIA - SQLAlchemy Models (ORM)
Reflete o schema PostgreSQL definido em migrations/init.sql
"""
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, Date, ForeignKey,
    UniqueConstraint, CheckConstraint, Index, BigInteger, JSON, Numeric, SmallInteger
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from database import Base


def gen_uuid():
    return uuid.uuid4()


# ============================================================
# 1. USERS
# ============================================================
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    avatar_url = Column(String(500))  # URL pública da foto (Azure Blob Storage)
    role = Column(String(20), default="user", index=True)  # user | admin | SUPER_ADMIN
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    # ============ Email verification (07/07/2026) ============
    verification_token = Column(String(64), index=True)  # single-use, expira em 24h
    verification_token_expires_at = Column(DateTime(timezone=True))
    verification_sent_at = Column(DateTime(timezone=True))  # rate-limit reenvio
    verified_at = Column(DateTime(timezone=True))  # quando clicou no link
    numerology_data = Column(JSONB)  # mapa numerológico calculado
    astrology_data = Column(JSONB)  # mapa astral completo (sol, lua, asc, planetas, casas)
    profile_status = Column(String(50), default="pending")  # pending|calculating|ready|failed
    onboarding_status = Column(String(50), default="pending")  # pending|in_progress|completed|skipped
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))

    # ============ BILLING / PLANOS / CRÉDITOS ============
    selected_plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id", ondelete="SET NULL"), index=True)
    credit_balance = Column(Integer, nullable=False, default=0)  # saldo atual (nunca negativo)
    credit_status = Column(String(50), nullable=False, default="inactive")  # inactive|active|exhausted|suspended
    plan_selected_at = Column(DateTime(timezone=True))
    billing_status = Column(String(50), nullable=False, default="billing_not_enabled")  # billing_not_enabled|active|past_due|canceled|trialing
    billing_provider = Column(String(50))  # stripe|asaas|mercadopago|null (futuro)
    external_customer_id = Column(String(255))
    external_subscription_id = Column(String(255))
    next_renewal_date = Column(DateTime(timezone=True))
    credits_last_granted_at = Column(DateTime(timezone=True))

    # ============ BLOCK (controle de acesso manual pelo admin) ============
    blocked_until = Column(DateTime(timezone=True))  # NULL = sem bloqueio OR permanente quando blocked_at != NULL e blocked_until NULL
    blocked_at    = Column(DateTime(timezone=True))  # quando foi bloqueado (NULL = desbloqueado)
    blocked_by    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))  # admin que bloqueou
    block_reason  = Column(Text)  # motivo / justificativa

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
    attributes = Column(JSONB, default=dict)  # dados dinâmicos do perfil
    onboarding_completed = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")


# ============================================================
# 3. ATTRIBUTE_DEFINITIONS (catálogo - configurável pelo admin)
# ============================================================
class AttributeDefinition(Base):
    """Catálogo de definições de atributos (configurado pelo admin)"""
    __tablename__ = "attribute_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    code = Column(String(100), unique=True, nullable=False, index=True)
    label = Column(String(255), nullable=False)
    description = Column(Text)
    attribute_type = Column(String(50), nullable=False)  # text|date|select|multiselect|...
    options = Column(JSONB)  # [{"value":"x","label":"X"}]
    is_required = Column(Boolean, default=False)
    is_onboarding = Column(Boolean, default=True)
    order_index = Column(Integer, default=0)
    validation_rules = Column(JSONB)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


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
# 5. CHATS
# ============================================================
class Chat(Base):
    __tablename__ = "chats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255))
    summary = Column(Text)
    context_snapshot = Column(JSONB)  # perfil no momento da conversa
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_message_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at")
    supervisor_analyses = relationship("SupervisorAnalysis", back_populates="chat", cascade="all, delete-orphan")


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
from sqlalchemy.dialects.postgresql import ARRAY as PgArray

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


# ============================================================
# 6. MESSAGES
# ============================================================
class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user|assistant|system
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer)
    ai_model = Column(String(100))
    metadata_json = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    supervisor_analyses = relationship("SupervisorAnalysis", back_populates="message", cascade="all, delete-orphan")

    chat = relationship("Chat", back_populates="messages")
    user = relationship("User", back_populates="messages")


# ============================================================
# 7. KNOWLEDGE_DOCUMENTS
# ============================================================
class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    file_name = Column(String(255))
    file_size_bytes = Column(BigInteger)
    storage_url = Column(Text)
    storage_provider = Column(String(50), default="azure_blob")
    file_hash = Column(String(128), index=True)
    status = Column(String(50), default="pending")  # pending|processing|indexed|failed
    error_message = Column(Text)
    chunks_count = Column(Integer, default=0)
    indexed_at = Column(DateTime(timezone=True))
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    collection = Column(String(100), default="conhecimento_geral")
    metadata_json = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    uploader = relationship("User", back_populates="documents_uploaded")


# ============================================================
# 8. AUDIT_LOG
# ============================================================
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50))
    resource_id = Column(UUID(as_uuid=True))
    details = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# ============================================================
# 9. PLANS (planos comerciais — Básico, Intermediário, Premium)
# ============================================================
class Plan(Base):
    __tablename__ = "plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    name = Column(String(100), nullable=False)  # "Básico", "Intermediário", "Premium"
    slug = Column(String(50), unique=True, nullable=False, index=True)  # basico|intermediario|premium
    credits = Column(Integer, nullable=False)  # créditos concedidos ao assinar
    price_brl = Column(Numeric(10, 2), nullable=False)  # preço em reais (referência)
    active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="selected_plan", foreign_keys="User.selected_plan_id")


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
    reference_type = Column(String(50))  # ex: chat_message, admin_adjust, migration
    reference_id = Column(String(100))  # ex: message_id
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="credit_transactions")


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

    # ✅ TRUE = análise veio da IA (model_used contém 'minimax' ou similar)
    # FALSE = veio só do pré-check regex (batch ainda não confirmou)
    # NULL = legado (anterior a essa coluna)
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

    # Relationships
    user = relationship("User", back_populates="supervisor_daily_summaries")


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
