"""
AttributeDefinition (catálogo de atributos - configurável pelo admin)
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from ._base import Base, gen_uuid


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
