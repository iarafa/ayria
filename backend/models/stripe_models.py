"""
Stripe: StripeSubscription, StripeInvoice, StripeWebhookEvent
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ._base import Base, gen_uuid


# ============================================================
# 18. STRIPE_SUBSCRIPTIONS (19/07/2026)
# Uma row por assinatura Stripe. User pode ter várias no histórico
# (canceladas), mas só UMA ativa por vez (regra de duplicação).
# ============================================================
class StripeSubscription(Base):
    __tablename__ = "stripe_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    ayria_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    stripe_customer_id = Column(String(100), nullable=False, index=True)
    stripe_subscription_id = Column(String(100), unique=True, nullable=False)
    stripe_product_id = Column(String(100))
    stripe_price_id = Column(String(100))
    plan_slug = Column(String(50), nullable=False)  # basic | premium | gold
    plan_name = Column(String(100))
    subscription_status = Column(String(50), nullable=False, index=True)  # active|trialing|past_due|unpaid|canceled|incomplete|incomplete_expired
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    cancel_at_period_end = Column(Boolean, default=False)
    last_payment_status = Column(String(50))
    metadata_json = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="stripe_subscriptions")


# ============================================================
# 19. STRIPE_INVOICES (19/07/2026)
# Histórico de faturas — uma row por invoice da Stripe.
# ============================================================
class StripeInvoice(Base):
    __tablename__ = "stripe_invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    ayria_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    stripe_invoice_id = Column(String(100), unique=True, nullable=False)
    stripe_subscription_id = Column(String(100))
    amount_total = Column(Integer)  # em centavos (ex: 4990 = R$ 49,90)
    currency = Column(String(10), default="brl")
    status = Column(String(50), nullable=False, index=True)  # paid|open|uncollectible|void
    paid_at = Column(DateTime(timezone=True))
    invoice_pdf_url = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", backref="stripe_invoices")


# ============================================================
# 20. STRIPE_WEBHOOK_EVENTS (19/07/2026)
# Tabela de idempotência — Stripe reenvia webhooks em caso de falha,
# então deduplicamos por stripe_event_id (UNIQUE).
# ============================================================
class StripeWebhookEvent(Base):
    __tablename__ = "stripe_webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    stripe_event_id = Column(String(100), unique=True, nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)
    processed_at = Column(DateTime(timezone=True))
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
