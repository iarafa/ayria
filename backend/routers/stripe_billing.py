"""
AYRIA - Stripe Billing Router (19/07/2026)

POST /api/stripe/create-checkout-session  — cria sessão de checkout (subscription)
POST /api/stripe/webhook                  — recebe eventos Stripe (HMAC validado + idempotente)
POST /api/stripe/create-portal-session    — abre Customer Portal (gerenciar assinatura)
GET  /api/stripe/config                   — public, retorna publishable_key + price_id por plano
GET  /api/stripe/me                       — assinatura ativa do user logado + status

SEGURANÇA:
- STRIPE_SECRET_KEY + STRIPE_WEBHOOK_SECRET nunca saem daqui (só server)
- Webhook valida assinatura HMAC OBRIGATORIAMENTE
- Idempotência: dedup por stripe_event_id (UNIQUE em stripe_webhook_events)
- Bloqueia assinatura duplicada pra mesmo user (regra de negócio)
"""
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, settings
from utils.security import get_current_user
import models
from services.credit_service import grant_credits

logger = logging.getLogger("stripe_billing")

router = APIRouter(tags=["stripe"])

# Configura o SDK Stripe com a secret key (UMA VEZ no startup do módulo)
stripe.api_key = settings.STRIPE_SECRET_KEY

# Planos disponíveis — slug -> (price_id_env_var, tokens_inclusos, display_name)
# Slugs devem bater com a tabela `plans` do DB (19/07/2026 — alinhado com Rafael).
PLANS = {
    "basico":        {"price_env": "STRIPE_PRICE_BASIC",   "tokens": 100,  "name": "Básico",        "price_brl": 29.90},
    "intermediario": {"price_env": "STRIPE_PRICE_PREMIUM", "tokens": 500,  "name": "Intermediário", "price_brl": 59.90},
    "premium":       {"price_env": "STRIPE_PRICE_GOLD",    "tokens": 1000, "name": "Premium",       "price_brl": 99.90},
}


def _resolve_price_id(plan_slug: str) -> str:
    """Retorna o Stripe price_id do plano. 404 se plano inválido."""
    plan = PLANS.get(plan_slug)
    if not plan:
        raise HTTPException(404, f"Plano '{plan_slug}' não existe. Planos válidos: {list(PLANS.keys())}")
    price_id = getattr(settings, plan["price_env"], "")
    if not price_id:
        raise HTTPException(500, f"STRIPE_PRICE_* não configurado para plano {plan_slug}")
    return price_id


def _resolve_plan_slug_by_price_id(price_id: str) -> Optional[str]:
    """Inverso: dado um price_id do Stripe, retorna o slug do plano."""
    for slug, cfg in PLANS.items():
        if getattr(settings, cfg["price_env"], "") == price_id:
            return slug
    return None


# ============================================================
# GET /api/stripe/config — público, frontend usa pra mostrar planos
# ============================================================
@router.get("/api/stripe/config")
async def get_stripe_config():
    """Retorna publishable_key + info dos planos. NÃO expõe secret."""
    if not settings.STRIPE_PUBLISHABLE_KEY:
        raise HTTPException(500, "Stripe não configurado no backend")
    return {
        "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "app_url": settings.APP_URL,
        "plans": [
            {
                "slug": slug,
                "name": cfg["name"],
                "tokens": cfg["tokens"],
                "price_brl": cfg["price_brl"],
                "price_id": getattr(settings, cfg["price_env"], ""),
            }
            for slug, cfg in PLANS.items()
        ],
    }


# ============================================================
# GET /api/stripe/me — assinatura ativa do user logado
# ============================================================
@router.get("/api/stripe/me")
async def get_my_subscription(
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna assinatura ativa + status + plano + próxima cobrança."""
    res = await db.execute(
        select(models.StripeSubscription)
        .where(models.StripeSubscription.ayria_user_id == user.id)
        .order_by(models.StripeSubscription.created_at.desc())
    )
    subs = res.scalars().all()
    active = next((s for s in subs if s.subscription_status in ("active", "trialing")), None)

    return {
        "user_id": str(user.id),
        "billing_status": user.billing_status or "billing_not_enabled",
        "billing_provider": user.billing_provider,
        "blocked_until": user.blocked_until.isoformat() if user.blocked_until else None,
        "credit_balance": user.credit_balance,
        "active_subscription": {
            "id": str(active.id),
            "plan_slug": active.plan_slug,
            "plan_name": active.plan_name,
            "status": active.subscription_status,
            "current_period_end": active.current_period_end.isoformat() if active.current_period_end else None,
            "cancel_at_period_end": active.cancel_at_period_end,
            "stripe_subscription_id": active.stripe_subscription_id,
        } if active else None,
        "history": [
            {
                "id": str(s.id),
                "plan_slug": s.plan_slug,
                "plan_name": s.plan_name,
                "status": s.subscription_status,
                "created_at": s.created_at.isoformat(),
            }
            for s in subs[:10]
        ],
    }


# ============================================================
# POST /api/stripe/create-checkout-session
# ============================================================
class CheckoutRequest(BaseModel):
    plan_slug: str  # basic | premium | gold
    coupon_code: Optional[str] = None  # 🆕 20/07 22:58 — cupom de desconto opcional


@router.post("/api/stripe/create-checkout-session")
async def create_checkout_session(
    body: CheckoutRequest,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cria Checkout Session e retorna URL de redirect."""
    if not user.is_verified:
        raise HTTPException(403, "Email precisa ser verificado antes de assinar")

    price_id = _resolve_price_id(body.plan_slug)
    plan_cfg = PLANS[body.plan_slug]

    # REGRA: bloqueia assinatura duplicada
    res = await db.execute(
        select(models.StripeSubscription)
        .where(
            and_(
                models.StripeSubscription.ayria_user_id == user.id,
                models.StripeSubscription.subscription_status.in_(("active", "trialing", "past_due")),
            )
        )
    )
    existing = res.scalars().first()
    if existing:
        raise HTTPException(
            409,
            f"Você já tem assinatura ativa (status={existing.subscription_status}). "
            "Use o Portal do Assinante pra mudar de plano ou cancelar."
        )

    # Se user tem subscription canceled mas ainda dentro do período pago → também bloqueia
    res = await db.execute(
        select(models.StripeSubscription)
        .where(
            and_(
                models.StripeSubscription.ayria_user_id == user.id,
                models.StripeSubscription.subscription_status == "canceled",
                models.StripeSubscription.current_period_end > datetime.now(timezone.utc),
            )
        )
    )
    canceled_active = res.scalars().first()
    if canceled_active:
        raise HTTPException(
            409,
            "Você tem assinatura cancelada mas ainda dentro do período pago. "
            "Use o Portal do Assinante."
        )

    try:
        session_params = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "customer_email": user.email,
            "client_reference_id": str(user.id),
            "metadata": {
                "ayria_user_id": str(user.id),
                "plan_slug": body.plan_slug,
                "plan_name": plan_cfg["name"],
            },
            "subscription_data": {
                "metadata": {
                    "ayria_user_id": str(user.id),
                    "plan_slug": body.plan_slug,
                    "plan_name": plan_cfg["name"],
                },
            },
            "success_url": f"{settings.APP_URL}/#/pagamento/sucesso?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{settings.APP_URL}/#/planos",
        }

        # 🆕 20/07 22:58 — Aplica cupom se informado
        if body.coupon_code:
            coupon_code = body.coupon_code.strip().upper()
            # Valida cupom no banco
            from models import Coupon, Partner
            coupon_q = await db.execute(select(Coupon).where(Coupon.code == coupon_code))
            coupon = coupon_q.scalar_one_or_none()
            if not coupon or not coupon.active:
                raise HTTPException(400, f"Cupom '{coupon_code}' inválido ou desativado")
            if coupon.expires_at and coupon.expires_at < datetime.now(timezone.utc):
                raise HTTPException(400, "Cupom expirado")
            if coupon.applicable_plan_slug != body.plan_slug:
                raise HTTPException(400, f"Cupom válido apenas para o plano {coupon.applicable_plan_slug}")
            # Passa pro Stripe
            session_params["discounts"] = [{"coupon": coupon.stripe_coupon_id}]
            session_params["metadata"]["coupon_code"] = coupon_code
            session_params["metadata"]["coupon_id"] = str(coupon.id)
            if coupon.partner_id:
                session_params["metadata"]["partner_id"] = str(coupon.partner_id)
            logger.info(f"Coupon applied: code={coupon_code} stripe_id={coupon.stripe_coupon_id} plan={body.plan_slug}")

        session = await stripe.checkout.Session.create_async(**session_params)
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating session: {e}")
        raise HTTPException(502, f"Erro Stripe: {e.user_message or str(e)}")

    logger.info(f"Checkout session created for user {user.id} plan={body.plan_slug} session_id={session.id}")
    return {
        "session_id": session.id,
        "url": session.url,
        "plan_slug": body.plan_slug,
    }


# ============================================================
# POST /api/stripe/create-portal-session
# ============================================================
@router.post("/api/stripe/create-portal-session")
async def create_portal_session(
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cria sessão do Customer Portal da Stripe (gerenciar assinatura)."""
    if not user.external_customer_id:
        raise HTTPException(404, "Você não tem assinatura Stripe ainda")

    try:
        session = await stripe.billing_portal.Session.create_async(
            customer=user.external_customer_id,
            return_url=f"{settings.APP_URL}/#/minha-conta",
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe portal error: {e}")
        raise HTTPException(502, f"Erro Stripe: {e.user_message or str(e)}")

    return {"url": session.url}


# ============================================================
# POST /api/stripe/webhook — RECEBE EVENTOS DO STRIPE
# ============================================================
@router.post("/api/stripe/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Recebe webhook do Stripe. Valida HMAC + dedup idempotente."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(500, "STRIPE_WEBHOOK_SECRET não configurado")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # 1. VALIDAR ASSINATURA HMAC
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.warning(f"Webhook payload inválido: {e}")
        raise HTTPException(400, "Payload inválido")
    except stripe.error.SignatureVerificationError as e:
        logger.warning(f"Webhook assinatura inválida: {e}")
        raise HTTPException(400, "Assinatura HMAC inválida")

    event_id = event["id"]
    event_type = event["type"]
    event_obj = event["data"]["object"]

    # Converte event_obj pra dict puro (Stripe Object não é JSON-serializável e quebra
    # quando usamos .get() em alguns métodos)
    def _to_plain_dict(obj):
        if obj is None:
            return {}
        if isinstance(obj, dict):
            return obj
        # Stripe Object: serializa via Stripe API representation
        try:
            return obj.to_dict() if hasattr(obj, 'to_dict') else dict(obj)
        except Exception:
            return {}

    event_obj = _to_plain_dict(event_obj)

    # Stripe SDK retorna objeto Event (não dict puro). Converte pra dict puro pra JSONB.
    # Stripe SDK >= 14 retorna stripe.Event que é dict-like mas NAO é JSON-serializável diretamente.
    def _stripe_to_dict(obj):
        """Serializa recursivamente Stripe Object → dict puro."""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, dict):
            return {k: _stripe_to_dict(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_stripe_to_dict(v) for v in obj]
        # Stripe Object
        try:
            return _stripe_to_dict(dict(obj))
        except Exception:
            return str(obj)

    try:
        event_payload = _stripe_to_dict(event)
    except Exception as e:
        logger.warning(f"Falha ao serializar event payload: {e}")
        event_payload = {"id": event_id, "type": event_type, "error": str(e)[:200]}

    # 2. DEDUP — verifica se já processamos esse event_id
    res = await db.execute(
        select(models.StripeWebhookEvent)
        .where(models.StripeWebhookEvent.stripe_event_id == event_id)
    )
    already = res.scalars().first()
    if already:
        logger.info(f"Webhook event {event_id} já processado ({event_type}) — ignorando")
        return {"status": "already_processed", "event_id": event_id}

    # 3. PERSISTIR o evento (idempotência: UNIQUE em stripe_event_id)
    try:
        wh_event = models.StripeWebhookEvent(
            stripe_event_id=event_id,
            event_type=event_type,
            payload=event_payload,
            processed_at=datetime.now(timezone.utc),
        )
        db.add(wh_event)
        await db.flush()
    except Exception as e:
        # Se UNIQUE conflict aqui, é outro worker que processou em paralelo
        logger.warning(f"INSERT webhook_event falhou: type={type(e).__name__} msg={str(e)[:200]}")
        await db.rollback()
        logger.info(f"Race condition dedup: {event_id} já inserido — ok")
        return {"status": "already_processed", "event_id": event_id}

    # 4. PROCESSAR EVENTO
    try:
        handler = _EVENT_HANDLERS.get(event_type)
        if handler:
            await handler(event_obj, db)
            logger.info(f"Webhook {event_type} processed for {event_id}")
        else:
            logger.debug(f"Webhook {event_type} sem handler (ignorado)")
        await db.commit()
    except Exception as e:
        await db.rollback()
        # Marca como failed (mas mantém UNIQUE pra não reprocessar)
        try:
            wh_event.error = str(e)[:1000]
            wh_event.processed_at = None
            db.add(wh_event)
            await db.commit()
        except Exception:
            pass
        logger.exception(f"Erro processando webhook {event_type}: {e}")
        raise HTTPException(500, f"Erro processando evento: {e}")

    return {"status": "ok", "event_id": event_id, "type": event_type}


# ============================================================
# HANDLERS POR TIPO DE EVENTO
# ============================================================
async def _resolve_user_id_from_event(event_obj: dict) -> Optional[str]:
    """Extrai ayria_user_id do evento Stripe."""
    # Prioridade 1: metadata.ayria_user_id (vem em todos os tipos)
    meta = event_obj.get("metadata") or {}
    if meta.get("ayria_user_id"):
        return meta["ayria_user_id"]
    # Prioridade 2: client_reference_id (só em checkout.session)
    if event_obj.get("client_reference_id"):
        return event_obj["client_reference_id"]
    # Prioridade 3: customer → buscar no DB
    customer_id = event_obj.get("customer")
    if customer_id:
        return None  # caller vai buscar via customer_id
    return None


async def _get_user_by_customer(customer_id: str, db: AsyncSession):
    res = await db.execute(
        select(models.User).where(models.User.external_customer_id == customer_id)
    )
    return res.scalars().first()


async def _handle_checkout_session_completed(event_obj, db):
    """checkout.session.completed — relaciona pagamento ao user."""
    user_id = await _resolve_user_id_from_event(event_obj)
    if not user_id:
        # fallback: busca via customer
        customer_id = event_obj.get("customer")
        if customer_id:
            user = await _get_user_by_customer(customer_id, db)
            if user:
                user_id = str(user.id)
    if not user_id:
        logger.warning("checkout.session.completed sem ayria_user_id")
        return

    user = await db.get(models.User, uuid.UUID(user_id))
    if not user:
        logger.warning(f"User {user_id} não encontrado no checkout.session.completed")
        return

    # Atualiza user
    user.billing_provider = "stripe"
    user.external_customer_id = event_obj.get("customer")
    sub_id = event_obj.get("subscription")
    if sub_id:
        user.external_subscription_id = sub_id
    user.billing_status = "active"
    user.blocked_until = None  # limpa bloqueio
    logger.info(f"User {user.id} checkout completed → billing_status=active")


async def _handle_subscription_created(event_obj, db):
    """customer.subscription.created — insere/upsert em stripe_subscriptions."""
    sub_id = event_obj["id"]
    user_id = await _resolve_user_id_from_event(event_obj)
    if not user_id:
        logger.warning("customer.subscription.created sem ayria_user_id")
        return

    # Marca user como cliente Stripe (billing_provider)
    user = await db.get(models.User, uuid.UUID(user_id))
    if user and not user.billing_provider:
        user.billing_provider = "stripe"
        user.external_customer_id = event_obj.get("customer") or user.external_customer_id

    price_id = (event_obj.get("items", {}).get("data", [{}])[0] or {}).get("price", {}).get("id", "")
    plan_slug = _resolve_plan_slug_by_price_id(price_id) or "intermediario"
    plan_name = PLANS.get(plan_slug, {}).get("name", "Intermediário")

    # 🆕 19/07/2026 — sincroniza users.selected_plan_id a partir do plano do Stripe
    # Se o user não tinha plano setado (ex: cadastrou sem escolher / admin deletou), agora aplica.
    if user:
        plan_row = await db.execute(
            select(models.Plan).where(models.Plan.slug == plan_slug)
        )
        plan_db = plan_row.scalars().first()
        if plan_db and user.selected_plan_id is None:
            user.selected_plan_id = plan_db.id
            logger.info(f"User {user.email} → selected_plan_id={plan_db.slug} (via Stripe webhook)")

    # Upsert
    res = await db.execute(
        select(models.StripeSubscription)
        .where(models.StripeSubscription.stripe_subscription_id == sub_id)
    )
    sub = res.scalars().first()

    if not sub:
        sub = models.StripeSubscription(
            ayria_user_id=uuid.UUID(user_id),
            stripe_customer_id=event_obj["customer"],
            stripe_subscription_id=sub_id,
            stripe_product_id=(event_obj.get("items", {}).get("data", [{}])[0] or {}).get("price", {}).get("product"),
            stripe_price_id=price_id,
            plan_slug=plan_slug,
            plan_name=plan_name,
            subscription_status=event_obj["status"],
            current_period_start=_ts_to_dt(event_obj.get("current_period_start")),
            current_period_end=_ts_to_dt(event_obj.get("current_period_end")),
            cancel_at_period_end=event_obj.get("cancel_at_period_end", False),
            last_payment_status="active",
        )
        db.add(sub)
    else:
        sub.subscription_status = event_obj["status"]
        sub.current_period_start = _ts_to_dt(event_obj.get("current_period_start"))
        sub.current_period_end = _ts_to_dt(event_obj.get("current_period_end"))
        sub.cancel_at_period_end = event_obj.get("cancel_at_period_end", False)

    # Credita tokens do plano (1x na ativação / renovação)
    plan_cfg = PLANS.get(plan_slug, {})
    if plan_cfg.get("tokens") and event_obj["status"] in ("active", "trialing"):
        user = await db.get(models.User, uuid.UUID(user_id))
        if user:
            await grant_credits(
                db,
                user,
                plan_cfg["tokens"],
                f"Assinatura {plan_name} ativada",
                reference_type="stripe_subscription",
                reference_id=sub_id,
            )
            user.billing_status = event_obj["status"]
            user.credits_last_granted_at = datetime.now(timezone.utc)

    logger.info(f"Subscription {sub_id} upserted: status={event_obj['status']} plan={plan_slug}")


async def _handle_subscription_updated(event_obj, db):
    """customer.subscription.updated — atualiza plano + status."""
    sub_id = event_obj["id"]
    res = await db.execute(
        select(models.StripeSubscription)
        .where(models.StripeSubscription.stripe_subscription_id == sub_id)
    )
    sub = res.scalars().first()
    if not sub:
        logger.warning(f"Sub {sub_id} não encontrada pra update")
        return

    sub.subscription_status = event_obj["status"]
    sub.current_period_start = _ts_to_dt(event_obj.get("current_period_start"))
    sub.current_period_end = _ts_to_dt(event_obj.get("current_period_end"))
    sub.cancel_at_period_end = event_obj.get("cancel_at_period_end", False)

    # Atualiza plan_slug se mudou (upgrade/downgrade)
    price_id = (event_obj.get("items", {}).get("data", [{}])[0] or {}).get("price", {}).get("id", "")
    new_plan_slug = _resolve_plan_slug_by_price_id(price_id)
    if new_plan_slug and new_plan_slug != sub.plan_slug:
        sub.plan_slug = new_plan_slug
        sub.plan_name = PLANS.get(new_plan_slug, {}).get("name", new_plan_slug)

    # Atualiza user
    user = await db.get(models.User, sub.ayria_user_id)
    if user:
        user.billing_status = event_obj["status"]
        # 🆕 19/07/2026 — se plano mudou via Stripe (upgrade/downgrade), atualiza users.selected_plan_id
        if new_plan_slug:
            plan_row = await db.execute(
                select(models.Plan).where(models.Plan.slug == new_plan_slug)
            )
            plan_db = plan_row.scalars().first()
            if plan_db and user.selected_plan_id != plan_db.id:
                logger.info(f"User {user.email} plano alterado → {plan_db.slug}")
                user.selected_plan_id = plan_db.id
        # past_due → tolerância 3 dias
        if event_obj["status"] == "past_due":
            user.blocked_until = datetime.now(timezone.utc) + timedelta(days=3)
            logger.info(f"User {user.id} past_due → blocked_until +3d")
        else:
            user.blocked_until = None


async def _handle_subscription_deleted(event_obj, db):
    """customer.subscription.deleted — marca cancelamento."""
    sub_id = event_obj["id"]
    res = await db.execute(
        select(models.StripeSubscription)
        .where(models.StripeSubscription.stripe_subscription_id == sub_id)
    )
    sub = res.scalars().first()
    if sub:
        sub.subscription_status = "canceled"

    user = await db.get(models.User, sub.ayria_user_id) if sub else None
    if user:
        user.billing_status = "canceled"
        # Mantém acesso até fim do período se current_period_end > now
        if sub and sub.current_period_end and sub.current_period_end > datetime.now(timezone.utc):
            user.blocked_until = sub.current_period_end
            logger.info(f"User {user.id} canceled → blocked_until={user.blocked_until}")
        else:
            user.blocked_until = None
    logger.info(f"Subscription {sub_id} cancelada")


async def _handle_invoice_paid(event_obj, db):
    """invoice.paid — confirma pagamento + insere em stripe_invoices."""
    user_id = await _resolve_user_id_from_event(event_obj)
    if not user_id:
        customer_id = event_obj.get("customer")
        if customer_id:
            user = await _get_user_by_customer(customer_id, db)
            if user:
                user_id = str(user.id)
    if not user_id:
        logger.warning("invoice.paid sem ayria_user_id")
        return

    # Insere/atualiza invoice
    inv_id = event_obj["id"]
    res = await db.execute(
        select(models.StripeInvoice)
        .where(models.StripeInvoice.stripe_invoice_id == inv_id)
    )
    inv = res.scalars().first()
    if not inv:
        inv = models.StripeInvoice(
            ayria_user_id=uuid.UUID(user_id),
            stripe_invoice_id=inv_id,
            stripe_subscription_id=event_obj.get("subscription"),
            amount_total=event_obj.get("amount_paid") or event_obj.get("amount_due"),
            currency=event_obj.get("currency", "brl"),
            status="paid",
            paid_at=_ts_to_dt(event_obj.get("status_transitions", {}).get("paid_at")),
            invoice_pdf_url=event_obj.get("invoice_pdf"),
        )
        db.add(inv)
    else:
        inv.status = "paid"
        inv.paid_at = _ts_to_dt(event_obj.get("status_transitions", {}).get("paid_at"))

    # User fica active e desbloqueado
    user = await db.get(models.User, uuid.UUID(user_id))
    if user:
        user.billing_status = "active"
        user.blocked_until = None

    # Credita tokens da renovação (se for invoice recorrente, não primeira)
    sub_id = event_obj.get("subscription")
    if sub_id:
        res = await db.execute(
            select(models.StripeSubscription)
            .where(models.StripeSubscription.stripe_subscription_id == sub_id)
        )
        sub = res.scalars().first()
        if sub and sub.plan_slug:
            plan_cfg = PLANS.get(sub.plan_slug, {})
            if plan_cfg.get("tokens") and user:
                await grant_credits(
                    db,
                    user,
                    plan_cfg["tokens"],
                    f"Renovação {plan_cfg.get('name', sub.plan_slug)}",
                    reference_type="stripe_invoice",
                    reference_id=inv_id,
                )
                user.credits_last_granted_at = datetime.now(timezone.utc)
                logger.info(f"Renovação {sub.plan_slug}: +{plan_cfg['tokens']} tokens pra {user.id}")

    # 🆕 20/07 22:58 — Calcula comissão de parceiro se cupom foi aplicado
    discount = event_obj.get("discount") or {}
    discount_coupon = discount.get("coupon") or {}
    stripe_coupon_id = discount_coupon.get("id")
    if stripe_coupon_id:
        try:
            from services.commission_service import register_commission_for_invoice
            await register_commission_for_invoice(
                db,
                stripe_invoice_id=inv_id,
                stripe_subscription_id=event_obj.get("subscription", ""),
                stripe_customer_id=event_obj.get("customer", ""),
                amount_total_cents=event_obj.get("amount_paid") or event_obj.get("amount_due") or 0,
                amount_paid_cents=event_obj.get("amount_paid") or 0,
                discount_amount_cents=sum(d.get("amount", 0) for d in event_obj.get("total_discount_amounts", []) if isinstance(d, dict)),
                discount_coupon_id=stripe_coupon_id,
            )
        except Exception as e:
            logger.exception(f"Erro calculando comissão (não bloqueia webhook): {e}")


async def _handle_invoice_payment_failed(event_obj, db):
    """invoice.payment_failed — registra falha + ativa tolerância past_due + AVISA USER/ADMIN."""
    user_id = await _resolve_user_id_from_event(event_obj)
    if not user_id:
        customer_id = event_obj.get("customer")
        if customer_id:
            user = await _get_user_by_customer(customer_id, db)
            if user:
                user_id = str(user.id)
    if not user_id:
        return

    user = await db.get(models.User, uuid.UUID(user_id))
    if user:
        user.billing_status = "past_due"
        user.blocked_until = datetime.now(timezone.utc) + timedelta(days=3)
        logger.warning(f"User {user.id} payment_failed → past_due +3d")

    # Registra invoice failed
    inv_id = event_obj["id"]
    res = await db.execute(
        select(models.StripeInvoice)
        .where(models.StripeInvoice.stripe_invoice_id == inv_id)
    )
    if not res.scalars().first():
        inv = models.StripeInvoice(
            ayria_user_id=uuid.UUID(user_id),
            stripe_invoice_id=inv_id,
            stripe_subscription_id=event_obj.get("subscription"),
            amount_total=event_obj.get("amount_due"),
            currency=event_obj.get("currency", "brl"),
            status="open",  # failed = ainda open
        )
        db.add(inv)

    # ① Envia email pro user avisando que o cartão falhou
    # ② Envia alerta Telegram pro admin (Rafael)
    # ③ Roda em background (não bloqueia o webhook)
    if user:
        try:
            import asyncio
            asyncio.create_task(_notify_payment_failed(user, event_obj))
        except Exception as e:
            logger.error(f"Falha ao agendar notify_payment_failed: {e}")


async def _notify_payment_failed(user: models.User, event_obj: dict) -> None:
    """Notifica user (email) e admin (Telegram) sobre falha de pagamento."""
    from services.email_turbo import get_email_client, EmailServiceError
    from services.email_templates import payment_failed_email_html, payment_failed_email_text

    attempt = event_obj.get("attempt_count") or 1
    amount_due = (event_obj.get("amount_due") or 0) / 100  # centavos → reais

    # ① Email pro user
    try:
        update_url = f"{settings.APP_URL}/#/minha-conta"
        html = payment_failed_email_html(user.full_name, grace_days=3, retry_count=attempt, update_url=update_url)
        text = payment_failed_email_text(user.full_name, grace_days=3, retry_count=attempt, update_url=update_url)
        client = get_email_client()
        await client.send_email(
            to_email=user.email,
            subject="AYRIA — ⚠️ Problema no seu pagamento (cartão recusado)",
            body_html=html,
            body_text=text,
        )
        logger.info(f"Email payment_failed enviado pra {user.email}")
    except EmailServiceError as e:
        logger.error(f"Falha email payment_failed pra {user.email}: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado no email payment_failed: {e}")

    # ② Telegram pro admin (Rafael)
    try:
        import subprocess
        token_file = "/home/peron/.telegram_bots.env"
        try:
            with open(token_file) as f:
                for line in f:
                    if line.startswith("AVISOS_TOKEN="):
                        avisos_token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
                else:
                    avisos_token = None
        except Exception:
            avisos_token = None

        if not avisos_token:
            avisos_token = os.environ.get("AVISOS_TOKEN")

        if avisos_token:
            chat_id = 779495783  # Rafael
            text = (
                "⚠️ *FALHA DE PAGAMENTO*\n\n"
                f"User: {user.email}\n"
                f"Tentativa: #{attempt}\n"
                f"Valor: R$ {amount_due:.2f}\n"
                f"Plano: {user.selected_plan_slug or 'desconhecido'}\n"
                f"Status: past_due · bloqueio em 3 dias\n\n"
                f"_O user já recebeu email avisando pra atualizar cartão._"
            )
            cmd = [
                "curl", "-s", "-X", "POST",
                f"https://api.telegram.org/bot{avisos_token}/sendMessage",
                "-d", f"chat_id={chat_id}",
                "-d", f"text={text}",
                "-d", "parse_mode=Markdown",
            ]
            subprocess.run(cmd, timeout=10, check=False, capture_output=True)
            logger.info(f"Telegram alerta payment_failed enviado pra {chat_id}")
    except Exception as e:
        logger.error(f"Erro inesperado no Telegram payment_failed: {e}")


# Registry
_EVENT_HANDLERS = {
    "checkout.session.completed": _handle_checkout_session_completed,
    "customer.subscription.created": _handle_subscription_created,
    "customer.subscription.updated": _handle_subscription_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
    "invoice.paid": _handle_invoice_paid,
    "invoice.payment_failed": _handle_invoice_payment_failed,
}


def _ts_to_dt(ts: Optional[int]) -> Optional[datetime]:
    """Converte unix timestamp (segundos) pra datetime UTC."""
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


# import uuid no final pra evitar circular
import uuid