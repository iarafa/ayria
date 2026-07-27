"""
Partner: Partner, Coupon, CouponRedemption
"""
from sqlalchemy import Column, String, Text, Integer, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ._base import Base, gen_uuid


# ============================================================
# 21. PARTNERS (20/07/2026 22:54)
# Cadastro de parceiros que indicam clientes com cupom de desconto
# ============================================================
class Partner(Base):
    __tablename__ = "partners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20))
    document_type = Column(String(10))       # CPF | CNPJ
    document_number = Column(String(20))
    pix_key = Column(String(255))            # chave PIX pra repasse
    commission_pct = Column(Numeric(5, 2))   # opcional agora (comissão fica no coupon)
    notes = Column(Text)
    active = Column(Boolean, default=True, nullable=False, index=True)
    # 23/07/2026 — autenticação no Portal do Parceiro (separado do AYRIA)
    password_hash = Column(String(255))
    last_login_at = Column(DateTime(timezone=True))
    must_change_password = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    coupons = relationship("Coupon", back_populates="partner")
    redemptions = relationship("CouponRedemption", back_populates="partner")


# ============================================================
# 22. COUPONS (20/07/2026 22:54)
# Cupom de desconto — espelho do Stripe + dados AYRIA
# ============================================================
class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    code = Column(String(50), unique=True, nullable=False, index=True)
    stripe_coupon_id = Column(String(100), unique=True, nullable=False, index=True)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id", ondelete="SET NULL"), index=True)

    name = Column(String(200))
    discount_type = Column(String(10), nullable=False)   # 'percent' | 'fixed'
    discount_value = Column(Numeric(10, 2), nullable=False)

    applicable_plan_slug = Column(String(50), nullable=False, index=True)
    duration_months = Column(Integer, default=1, nullable=False)
    commission_pct = Column(Numeric(5, 2), nullable=False)

    max_redemptions = Column(Integer)                     # NULL = ilimitado
    current_redemptions = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime(timezone=True))          # NULL = sem expiração

    active = Column(Boolean, default=True, nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 🆕 26/07/2026 22:15 — Soft-delete: preserva histórico p/ portal do parceiro
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    deleted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    partner = relationship("Partner", back_populates="coupons")
    redemptions = relationship("CouponRedemption", back_populates="coupon")


# ============================================================
# 23. COUPON_REDEMPTIONS (20/07/2026 22:54)
# Log de uso do cupom + comissão gerada
# ============================================================
class CouponRedemption(Base):
    __tablename__ = "coupon_redemptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    coupon_id = Column(UUID(as_uuid=True), ForeignKey("coupons.id", ondelete="SET NULL"), index=True)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id", ondelete="SET NULL"), index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    stripe_invoice_id = Column(String(100), index=True)
    stripe_subscription_id = Column(String(100))

    plan_slug = Column(String(50), nullable=False)
    original_amount_cents = Column(Integer, nullable=False)
    discount_amount_cents = Column(Integer, nullable=False)
    final_amount_cents = Column(Integer, nullable=False)

    # 🆕 26/07/2026 22:15 — Snapshot do código p/ preservar histórico se cupom for hard-deletado
    coupon_code_snapshot = Column(String(50))

    commission_pct = Column(Numeric(5, 2))
    commission_amount_cents = Column(Integer)

    payout_status = Column(String(20), default="pending", nullable=False, index=True)  # pending|paid|cancelled
    payout_at = Column(DateTime(timezone=True))
    payout_notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    coupon = relationship("Coupon", back_populates="redemptions")
    partner = relationship("Partner", back_populates="redemptions")
    user = relationship("User", backref="coupon_redemptions")
