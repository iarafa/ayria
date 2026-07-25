"""
KnowledgeDocument
"""
from sqlalchemy import Column, String, Text, Integer, BigInteger, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ._base import Base, gen_uuid


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
