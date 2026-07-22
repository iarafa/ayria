"""
AYRIA - Cupons + Parceiros (20/07/2026 22:55)
Endpoints:
  ADMIN:
    GET    /api/admin/partners
    POST   /api/admin/partners
    PATCH  /api/admin/partners/{id}
    DELETE /api/admin/partners/{id}
    GET    /api/admin/coupons
    POST   /api/admin/coupons          (cria no Stripe + AYRIA)
    PATCH  /api/admin/coupons/{id}
    POST   /api/admin/coupons/{id}/deactivate
    GET    /api/admin/commissions
    POST   /api/admin/commissions/{id}/pay
  USER:
    POST   /api/coupons/validate        (público autenticado)
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import (
    User, Partner, Coupon, CouponRedemption,
)
import schemas
from utils.security import get_current_user, require_admin

logger = logging.getLogger("coupons")

router = APIRouter(tags=["coupons"])

# ============================================================
# HELPERS
# ============================================================

def _partner_to_response(p: Partner, coupons_count: int = 0, total_commission_cents: int = 0) -> schemas.PartnerResponse:
    return schemas.PartnerResponse(
        id=str(p.id),
        name=p.name,
        email=p.email,
        phone=p.phone,
        document_type=p.document_type,
        document_number=p.document_number,
        pix_key=p.pix_key,
        commission_pct=float(p.commission_pct) if p.commission_pct else None,
        notes=p.notes,
        active=p.active,
        created_at=p.created_at.isoformat() if p.created_at else "",
        coupons_count=coupons_count,
        total_commission_cents=total_commission_cents,
    )


def _coupon_to_response(c: Coupon, partner_name: Optional[str] = None) -> schemas.CouponResponse:
    return schemas.CouponResponse(
        id=str(c.id),
        code=c.code,
        stripe_coupon_id=c.stripe_coupon_id,
        partner_id=str(c.partner_id) if c.partner_id else None,
        partner_name=partner_name,
        name=c.name,
        discount_type=c.discount_type,
        discount_value=float(c.discount_value),
        applicable_plan_slug=c.applicable_plan_slug,
        duration_months=c.duration_months,
        commission_pct=float(c.commission_pct),
        max_redemptions=c.max_redemptions,
        current_redemptions=c.current_redemptions,
        expires_at=c.expires_at.isoformat() if c.expires_at else None,
        active=c.active,
        created_at=c.created_at.isoformat() if c.created_at else "",
    )


def calc_discount_cents(plan_price_cents: int, discount_type: str, discount_value: float) -> int:
    """Calcula desconto em centavos."""
    if discount_type == "percent":
        return int(round(plan_price_cents * (discount_value / 100)))
    elif discount_type == "fixed":
        return int(round(discount_value * 100))  # valor em reais → centavos
    else:
        raise ValueError(f"discount_type inválido: {discount_type}")


# ============================================================
# ADMIN: PARTNERS CRUD
# ============================================================

@router.get("/api/admin/partners", response_model=list[schemas.PartnerResponse])
async def list_partners(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    active_only: bool = Query(False),
):
    """Lista todos os parceiros."""
    stmt = select(Partner).order_by(Partner.created_at.desc())
    if active_only:
        stmt = stmt.where(Partner.active == True)
    result = await db.execute(stmt)
    partners = result.scalars().all()

    # Conta cupons por parceiro
    coupon_counts_q = select(Coupon.partner_id, func.count(Coupon.id)).group_by(Coupon.partner_id)
    coupon_counts = {row[0]: row[1] for row in (await db.execute(coupon_counts_q)).all()}

    # Comissão total pendente
    commission_q = select(CouponRedemption.partner_id, func.coalesce(func.sum(CouponRedemption.commission_amount_cents), 0))\
        .where(CouponRedemption.payout_status == "pending")\
        .group_by(CouponRedemption.partner_id)
    commissions = {row[0]: row[1] for row in (await db.execute(commission_q)).all()}

    return [
        _partner_to_response(p, coupon_counts.get(p.id, 0), commissions.get(p.id, 0))
        for p in partners
    ]


@router.post("/api/admin/partners", response_model=schemas.PartnerResponse, status_code=201)
async def create_partner(
    body: schemas.PartnerCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Cria novo parceiro."""
    # Validação: email único
    existing = await db.execute(select(Partner).where(Partner.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Já existe parceiro com email {body.email}")

    partner = Partner(
        name=body.name,
        email=body.email,
        phone=body.phone,
        document_type=body.document_type,
        document_number=body.document_number,
        pix_key=body.pix_key,
        commission_pct=Decimal(str(body.commission_pct)) if body.commission_pct else None,
        notes=body.notes,
        active=True,
    )
    db.add(partner)
    await db.commit()
    await db.refresh(partner)
    logger.info(f"Partner created: {partner.id} email={partner.email}")
    return _partner_to_response(partner)


@router.patch("/api/admin/partners/{partner_id}", response_model=schemas.PartnerResponse)
async def update_partner(
    partner_id: str,
    body: schemas.PartnerUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Atualiza parceiro."""
    from uuid import UUID
    try:
        pid = UUID(partner_id)
    except ValueError:
        raise HTTPException(400, "ID inválido")

    partner = await db.get(Partner, pid)
    if not partner:
        raise HTTPException(404, "Parceiro não encontrado")

    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        if k == "commission_pct" and v is not None:
            v = Decimal(str(v))
        setattr(partner, k, v)

    await db.commit()
    await db.refresh(partner)
    logger.info(f"Partner updated: {partner.id}")
    return _partner_to_response(partner)


@router.delete("/api/admin/partners/{partner_id}", status_code=204)
async def delete_partner(
    partner_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete: marca active=False (preserva histórico de cupons)."""
    from uuid import UUID
    try:
        pid = UUID(partner_id)
    except ValueError:
        raise HTTPException(400, "ID inválido")

    partner = await db.get(Partner, pid)
    if not partner:
        raise HTTPException(404, "Parceiro não encontrado")

    partner.active = False
    await db.commit()
    logger.info(f"Partner deactivated: {partner.id}")
    return None


# ============================================================
# ADMIN: COUPONS CRUD
# ============================================================

@router.get("/api/admin/coupons", response_model=list[schemas.CouponResponse])
async def list_coupons(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    active_only: bool = Query(False),
):
    """Lista todos os cupons."""
    stmt = select(Coupon, Partner).outerjoin(Partner, Coupon.partner_id == Partner.id)\
        .order_by(Coupon.created_at.desc())
    if active_only:
        stmt = stmt.where(Coupon.active == True)
    result = await db.execute(stmt)
    rows = result.all()
    return [_coupon_to_response(c, p.name if p else None) for c, p in rows]


@router.post("/api/admin/coupons", response_model=schemas.CouponResponse, status_code=201)
async def create_coupon(
    body: schemas.CouponCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Cria cupom no Stripe + espelha no AYRIA."""
    from uuid import UUID

    # Validação
    if body.discount_type not in ("percent", "fixed"):
        raise HTTPException(400, "discount_type deve ser 'percent' ou 'fixed'")
    if body.discount_value <= 0:
        raise HTTPException(400, "discount_value deve ser > 0")
    if body.duration_months < 1:
        raise HTTPException(400, "duration_months deve ser >= 1")
    if body.commission_pct < 0 or body.commission_pct > 100:
        raise HTTPException(400, "commission_pct deve estar entre 0 e 100")

    # Verifica se código já existe
    existing = await db.execute(select(Coupon).where(Coupon.code == body.code.upper()))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Código '{body.code}' já existe")

    # Verifica se plano existe (no PLANS dict)
    from routers.stripe_billing import PLANS
    if body.applicable_plan_slug not in PLANS:
        raise HTTPException(400, f"Plano '{body.applicable_plan_slug}' não existe")

    # Verifica partner se informado
    partner = None
    if body.partner_id:
        try:
            pid = UUID(body.partner_id)
        except ValueError:
            raise HTTPException(400, "partner_id inválido")
        partner = await db.get(Partner, pid)
        if not partner:
            raise HTTPException(400, f"Parceiro {body.partner_id} não encontrado")
        if not partner.active:
            raise HTTPException(400, "Parceiro inativo")

    # Cria coupon no Stripe
    stripe_params = {
        "name": body.name or body.code.upper(),
        "duration": "repeating",
        "duration_in_months": body.duration_months,
    }
    if body.discount_type == "percent":
        stripe_params["percent_off"] = body.discount_value
    else:
        stripe_params["amount_off"] = int(round(body.discount_value * 100))  # em centavos
        stripe_params["currency"] = "brl"

    if body.max_redemptions:
        stripe_params["max_redemptions"] = body.max_redemptions
    if body.expires_at:
        stripe_params["redeem_by"] = int(datetime.fromisoformat(body.expires_at).timestamp())

    try:
        stripe_coupon = await stripe.Coupon.create_async(**stripe_params)
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating coupon: {e}")
        raise HTTPException(502, f"Erro Stripe: {e.user_message or str(e)}")

    # Cria no AYRIA
    coupon = Coupon(
        code=body.code.upper(),
        stripe_coupon_id=stripe_coupon.id,
        partner_id=partner.id if partner else None,
        name=body.name,
        discount_type=body.discount_type,
        discount_value=Decimal(str(body.discount_value)),
        applicable_plan_slug=body.applicable_plan_slug,
        duration_months=body.duration_months,
        commission_pct=Decimal(str(body.commission_pct)),
        max_redemptions=body.max_redemptions,
        expires_at=datetime.fromisoformat(body.expires_at) if body.expires_at else None,
        active=True,
        created_by=admin.id,
    )
    db.add(coupon)
    await db.commit()
    await db.refresh(coupon)
    logger.info(f"Coupon created: code={coupon.code} stripe_id={coupon.stripe_coupon_id} partner={partner.email if partner else None}")
    return _coupon_to_response(coupon, partner.name if partner else None)


@router.patch("/api/admin/coupons/{coupon_id}", response_model=schemas.CouponResponse)
async def update_coupon(
    coupon_id: str,
    body: schemas.CouponUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Atualiza metadados do cupom (NÃO muda o desconto no Stripe)."""
    from uuid import UUID
    try:
        cid = UUID(coupon_id)
    except ValueError:
        raise HTTPException(400, "ID inválido")

    coupon = await db.get(Coupon, cid)
    if not coupon:
        raise HTTPException(404, "Cupom não encontrado")

    updates = body.model_dump(exclude_unset=True)
    if "commission_pct" in updates and updates["commission_pct"] is not None:
        updates["commission_pct"] = Decimal(str(updates["commission_pct"]))
    if "expires_at" in updates and updates["expires_at"]:
        updates["expires_at"] = datetime.fromisoformat(updates["expires_at"])

    for k, v in updates.items():
        setattr(coupon, k, v)

    await db.commit()
    await db.refresh(coupon)
    logger.info(f"Coupon updated: {coupon.code}")
    partner = await db.get(Partner, coupon.partner_id) if coupon.partner_id else None
    return _coupon_to_response(coupon, partner.name if partner else None)


@router.post("/api/admin/coupons/{coupon_id}/deactivate", response_model=schemas.CouponResponse)
async def deactivate_coupon(
    coupon_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Desativa cupom (AYRIA + Stripe)."""
    from uuid import UUID
    try:
        cid = UUID(coupon_id)
    except ValueError:
        raise HTTPException(400, "ID inválido")

    coupon = await db.get(Coupon, cid)
    if not coupon:
        raise HTTPException(404, "Cupom não encontrado")

    coupon.active = False
    try:
        await stripe.Coupon.delete_async(coupon.stripe_coupon_id)
    except stripe.error.StripeError as e:
        logger.warning(f"Stripe coupon delete failed (continuando): {e}")

    await db.commit()
    await db.refresh(coupon)
    return _coupon_to_response(coupon)


# ============================================================
# ADMIN: COMMISSIONS (relatório)
# ============================================================

@router.get("/api/admin/commissions", response_model=schemas.CommissionReportResponse)
async def list_commissions(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    partner_id: Optional[str] = Query(None),
    payout_status: Optional[str] = Query(None),
):
    """Lista comissões (com filtros opcionais)."""
    from uuid import UUID

    stmt = select(CouponRedemption, Coupon, Partner, User)\
        .outerjoin(Coupon, CouponRedemption.coupon_id == Coupon.id)\
        .outerjoin(Partner, CouponRedemption.partner_id == Partner.id)\
        .outerjoin(User, CouponRedemption.user_id == User.id)\
        .order_by(CouponRedemption.created_at.desc())

    if partner_id:
        try:
            stmt = stmt.where(CouponRedemption.partner_id == UUID(partner_id))
        except ValueError:
            raise HTTPException(400, "partner_id inválido")
    if payout_status:
        stmt = stmt.where(CouponRedemption.payout_status == payout_status)

    result = await db.execute(stmt)
    rows = result.all()

    items = []
    total_pending = 0
    total_paid = 0
    for r, c, p, u in rows:
        if r.payout_status == "pending":
            total_pending += r.commission_amount_cents or 0
        elif r.payout_status == "paid":
            total_paid += r.commission_amount_cents or 0
        items.append({
            "id": str(r.id),
            "coupon_code": c.code if c else None,
            "partner_name": p.name if p else None,
            "user_email": u.email if u else None,
            "plan_slug": r.plan_slug,
            "original_amount_cents": r.original_amount_cents,
            "discount_amount_cents": r.discount_amount_cents,
            "final_amount_cents": r.final_amount_cents,
            "commission_pct": float(r.commission_pct) if r.commission_pct else None,
            "commission_amount_cents": r.commission_amount_cents,
            "payout_status": r.payout_status,
            "payout_at": r.payout_at.isoformat() if r.payout_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        })

    return schemas.CommissionReportResponse(
        items=items,
        total_pending_cents=total_pending,
        total_paid_cents=total_paid,
    )


@router.post("/api/admin/commissions/{redemption_id}/pay", status_code=200)
async def mark_commission_paid(
    redemption_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    notes: Optional[str] = None,
):
    """Marca comissão como paga (PIX manual feito)."""
    from uuid import UUID
    try:
        rid = UUID(redemption_id)
    except ValueError:
        raise HTTPException(400, "ID inválido")

    r = await db.get(CouponRedemption, rid)
    if not r:
        raise HTTPException(404, "Comissão não encontrada")
    if r.payout_status == "paid":
        raise HTTPException(400, "Já está marcada como paga")

    r.payout_status = "paid"
    r.payout_at = datetime.utcnow()
    r.payout_notes = notes
    await db.commit()
    logger.info(f"Commission paid: {r.id} amount_cents={r.commission_amount_cents}")
    return {"ok": True, "id": str(r.id)}


# ============================================================
# USER: VALIDATE CUPOM (público autenticado)
# ============================================================

@router.post("/api/coupons/validate", response_model=schemas.CouponValidateResponse)
async def validate_coupon(
    body: schemas.CouponValidateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Valida cupom e retorna preview do desconto."""
    from routers.stripe_billing import PLANS

    code = body.code.strip().upper()
    stmt = select(Coupon, Partner).outerjoin(Partner, Coupon.partner_id == Partner.id)\
        .where(Coupon.code == code)
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        return schemas.CouponValidateResponse(valid=False, error="Cupom não encontrado")
    coupon, partner = row

    if not coupon.active:
        return schemas.CouponValidateResponse(valid=False, error="Cupom desativado")

    if coupon.expires_at and coupon.expires_at < datetime.utcnow():
        return schemas.CouponValidateResponse(valid=False, error="Cupom expirado")

    if coupon.max_redemptions and coupon.current_redemptions >= coupon.max_redemptions:
        return schemas.CouponValidateResponse(valid=False, error="Cupom esgotado")

    if body.plan_slug and coupon.applicable_plan_slug != body.plan_slug:
        return schemas.CouponValidateResponse(
            valid=False,
            error=f"Cupom válido apenas para o plano {coupon.applicable_plan_slug}"
        )

    # Calcula preview do desconto (se user passou plan_slug)
    preview = None
    if body.plan_slug and body.plan_slug in PLANS:
        plan_price_cents = int(PLANS[body.plan_slug]["price_brl"] * 100)
        discount_cents = calc_discount_cents(plan_price_cents, coupon.discount_type, float(coupon.discount_value))
        final_cents = max(0, plan_price_cents - discount_cents)
        preview = {
            "original_cents": plan_price_cents,
            "discount_cents": discount_cents,
            "final_cents": final_cents,
            "currency": "brl",
        }

    return schemas.CouponValidateResponse(
        valid=True,
        coupon_id=str(coupon.id),
        code=coupon.code,
        name=coupon.name,
        discount_type=coupon.discount_type,
        discount_value=float(coupon.discount_value),
        applicable_plan_slug=coupon.applicable_plan_slug,
        duration_months=coupon.duration_months,
        partner_name=partner.name if partner else None,
        preview=preview,
    )
