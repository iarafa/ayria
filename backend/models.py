"""
AYRIA - SQLAlchemy Models (ORM)
Reflete o schema PostgreSQL definido em migrations/init.sql
"""
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, ForeignKey,
    UniqueConstraint, CheckConstraint, Index, BigInteger, JSON
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
    role = Column(String(20), default="user", index=True)  # user | admin | SUPER_ADMIN
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    numerology_data = Column(JSONB)  # mapa numerológico calculado
    astrology_data = Column(JSONB)  # mapa astral completo (sol, lua, asc, planetas, casas)
    profile_status = Column(String(50), default="pending")  # pending|calculating|ready|failed
    onboarding_status = Column(String(50), default="pending")  # pending|in_progress|completed|skipped
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    documents_uploaded = relationship("KnowledgeDocument", back_populates="uploader")


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
