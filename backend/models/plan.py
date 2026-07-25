"""
Plan (planos comerciais — Básico, Intermediário, Premium)
"""
from sqlalchemy import Column, String, Integer, Numeric, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ._base import Base, gen_uuid


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
