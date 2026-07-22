"""
AYRIA - Commission Service (20/07/2026 22:58)
Calcula comissão de parceiro quando invoice com cupom é paga.

Chamado pelo webhook handler do Stripe quando invoice.paid chega.
"""
import logging
from decimal import Decimal
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Coupon, CouponRedemption, Partner, User, StripeInvoice

logger = logging.getLogger("commission_service")


async def register_commission_for_invoice(
    db: AsyncSession,
    stripe_invoice_id: str,
    stripe_subscription_id: str,
    stripe_customer_id: str,
    amount_total_cents: int,
    amount_paid_cents: int,
    discount_amount_cents: int,
    discount_coupon_id: str,
) -> CouponRedemption | None:
    """
    Procura cupom AYRIA pelo stripe_coupon_id e registra comissão.
    
    Retorna CouponRedemption criada, ou None se:
    - Cupom não tá no AYRIA
    - Cupom não tem partner
    - Já tem redemption registrada pra essa invoice
    """
    # Idempotência: já registrou?
    existing = await db.execute(
        select(CouponRedemption).where(CouponRedemption.stripe_invoice_id == stripe_invoice_id)
    )
    if existing.scalar_one_or_none():
        logger.info(f"Redemption already exists for invoice {stripe_invoice_id} - skip")
        return None

    # Procura cupom AYRIA pelo stripe_coupon_id
    coupon_q = await db.execute(
        select(Coupon).where(Coupon.stripe_coupon_id == discount_coupon_id)
    )
    coupon = coupon_q.scalar_one_or_none()
    if not coupon:
        logger.info(f"Coupon with stripe_id {discount_coupon_id} not found in AYRIA - no commission")
        return None

    if not coupon.partner_id:
        logger.info(f"Coupon {coupon.code} has no partner - no commission")
        return None

    # Acha o user pela customer_id (StripeInvoice tem user_id)
    invoice_q = await db.execute(
        select(StripeInvoice).where(StripeInvoice.stripe_invoice_id == stripe_invoice_id)
    )
    invoice_row = invoice_q.scalar_one_or_none()
    user_id = invoice_row.ayria_user_id if invoice_row else None

    # Calcula comissão
    commission_cents = int(round(discount_amount_cents * (float(coupon.commission_pct) / 100)))

    redemption = CouponRedemption(
        coupon_id=coupon.id,
        partner_id=coupon.partner_id,
        user_id=user_id,
        stripe_invoice_id=stripe_invoice_id,
        stripe_subscription_id=stripe_subscription_id,
        plan_slug=coupon.applicable_plan_slug,
        original_amount_cents=amount_total_cents + discount_amount_cents,  # preço cheio
        discount_amount_cents=discount_amount_cents,
        final_amount_cents=amount_total_cents,
        commission_pct=coupon.commission_pct,
        commission_amount_cents=commission_cents,
        payout_status="pending",
    )
    db.add(redemption)

    # Incrementa contador de uso do cupom
    coupon.current_redemptions = (coupon.current_redemptions or 0) + 1

    await db.commit()
    await db.refresh(redemption)
    logger.info(
        f"Commission registered: invoice={stripe_invoice_id} coupon={coupon.code} "
        f"discount={discount_amount_cents}c commission={commission_cents}c partner={coupon.partner_id}"
    )
    return redemption
