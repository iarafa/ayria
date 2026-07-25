"""
Chat, Message
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ._base import Base, gen_uuid


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
    action_type_id = Column(UUID(as_uuid=True), ForeignKey("action_types.id", ondelete="SET NULL"), index=True, nullable=True)  # 21/07/2026 — custo variável
    metadata_json = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    supervisor_analyses = relationship("SupervisorAnalysis", back_populates="message", cascade="all, delete-orphan")

    chat = relationship("Chat", back_populates="messages")
    user = relationship("User", back_populates="messages")
