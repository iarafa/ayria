"""
AYRIA - Credit Service

Gerencia concessão e consumo de créditos.
Todas as operações são ATÔMICAS via transação do SQLAlchemy.

Regras de negócio:
- Grant inicial: idempotente (não duplica em retry do register)
- Consumo: bloqueia se saldo insuficiente (retorna tuple com flag)
- Toda movimentação gera CreditTransaction para auditoria
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional, Tuple
import logging
import uuid

import models

logger = logging.getLogger(__name__)


class InsufficientCreditsError(Exception):
    """Usuário não tem créditos suficientes"""
    def __init__(self, balance: int, required: int = 1):
        self.balance = balance
        self.required = required
        super().__init__(f"Saldo insuficiente: {balance} < {required}")


async def get_plan_by_slug(db: AsyncSession, slug: str) -> Optional[models.Plan]:
    """Busca plano pelo slug. Retorna None se não existir ou inativo."""
    if not slug:
        return None
    res = await db.execute(
        select(models.Plan).where(
            models.Plan.slug == slug,
            models.Plan.active == True,
        )
    )
    return res.scalar_one_or_none()


async def grant_initial_credits(
    db: AsyncSession,
    user: models.User,
    plan: models.Plan,
    description: Optional[str] = None,
    reference_type: str = "user_register",
    reference_id: Optional[str] = None,
) -> bool:
    """
    Concede créditos iniciais do plano. IDEMPOTENTE.

    Se o user já tem plan_selected_at e selected_plan_id preenchidos
    E já existe uma credit_transaction do tipo 'grant_initial_plan' pra ele,
    retorna False sem fazer nada.

    Retorna True se concedeu agora, False se já tinha sido concedido.
    """
    # Idempotência: se já tem plano + grant_initial_plan, não faz nada
    if user.selected_plan_id and user.plan_selected_at:
        existing = await db.execute(
            select(models.CreditTransaction)
            .where(
                models.CreditTransaction.user_id == user.id,
                models.CreditTransaction.type == "grant_initial_plan",
                models.CreditTransaction.reference_type == reference_type,
            )
            .limit(1)
        )
        if existing.scalar_one_or_none():
            logger.info(f"Grant inicial já existente pro user {user.id} — pulando")
            return False

    # Concede
    balance_before = user.credit_balance or 0
    user.selected_plan_id = plan.id
    user.credit_balance = balance_before + plan.credits
    user.credit_status = "active" if user.credit_balance > 0 else "exhausted"
    user.billing_status = user.billing_status or "billing_not_enabled"
    user.plan_selected_at = user.plan_selected_at or datetime.utcnow()
    user.credits_last_granted_at = datetime.utcnow()

    tx = models.CreditTransaction(
        id=uuid.uuid4(),
        user_id=user.id,
        type="grant_initial_plan",
        amount=plan.credits,
        balance_before=balance_before,
        balance_after=user.credit_balance,
        description=description or f"Créditos iniciais concedidos conforme plano {plan.name}",
        reference_type=reference_type,
        reference_id=reference_id or str(user.id),
    )
    db.add(tx)

    logger.info(f"✅ Grant inicial: user={user.id} plano={plan.slug} +{plan.credits} → saldo={user.credit_balance}")
    return True


async def consume_credits(
    db: AsyncSession,
    user: models.User,
    amount: int = 1,
    description: Optional[str] = None,
    reference_type: str = "chat_message",
    reference_id: Optional[str] = None,
) -> Tuple[bool, Optional[models.CreditTransaction]]:
    """
    Consome créditos. ATÔMICO — bloqueia se saldo insuficiente.

    Regras:
    - Se user.role in (admin, SUPER_ADMIN): bypass total (não consome, não registra)
    - Se onboarding incompleto: bypass (não consome, não registra) — onboarding é grátis
    - Se saldo < amount: retorna (False, None) SEM consumir
    - Caso contrário: desconta + registra transaction

    Retorna (success, transaction).
    """
    # Admin bypass — não consome nem registra
    if user.role in ("admin", "SUPER_ADMIN"):
        logger.debug(f"User admin {user.id} bypass de consumo de créditos")
        return True, None

    # Onboarding incompleto = grátis
    if user.onboarding_status != "completed":
        logger.debug(f"User {user.id} onboarding incompleto — sem consumo")
        return True, None

    # Bloqueio por saldo
    if (user.credit_balance or 0) < amount:
        logger.warning(f"❌ User {user.id} sem saldo: {user.credit_balance} < {amount}")
        return False, None

    # Consome
    balance_before = user.credit_balance
    user.credit_balance = balance_before - amount
    user.credit_status = "active" if user.credit_balance > 0 else "exhausted"

    tx = models.CreditTransaction(
        id=uuid.uuid4(),
        user_id=user.id,
        type="usage_chat_message",
        amount=-amount,  # negativo = consumo
        balance_before=balance_before,
        balance_after=user.credit_balance,
        description=description or f"Consumo de {amount} crédito(s) por mensagem no chat",
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(tx)

    logger.info(f"💸 Consumo: user={user.id} -{amount} → saldo={user.credit_balance}")
    return True, tx


async def admin_adjust_credits(
    db: AsyncSession,
    admin_user: models.User,
    target_user: models.User,
    amount: int,
    description: str,
    tx_type: str = "adjustment_manual",
) -> models.CreditTransaction:
    """
    Admin ajusta saldo manualmente (positivo ou negativo).

    amount > 0: bônus/adição
    amount < 0: remoção/penalidade

    Garante que saldo nunca fica negativo.
    """
    if not description or not description.strip():
        raise ValueError("description é obrigatório")

    if tx_type not in ("bonus_manual", "adjustment_manual", "recharge_future", "refund_future"):
        raise ValueError(f"Tipo inválido: {tx_type}")

    balance_before = target_user.credit_balance or 0
    new_balance = balance_before + amount

    if new_balance < 0:
        raise ValueError(f"Saldo ficaria negativo: {balance_before} + {amount} = {new_balance}")

    target_user.credit_balance = new_balance
    target_user.credit_status = "active" if new_balance > 0 else "exhausted"
    target_user.credits_last_granted_at = datetime.utcnow() if amount > 0 else target_user.credits_last_granted_at

    tx = models.CreditTransaction(
        id=uuid.uuid4(),
        user_id=target_user.id,
        type=tx_type,
        amount=amount,
        balance_before=balance_before,
        balance_after=new_balance,
        description=description.strip(),
        reference_type="admin_adjust",
        reference_id=str(admin_user.id),
    )
    db.add(tx)

    logger.info(f"🔧 Admin {admin_user.email} ajustou {amount} créditos do user {target_user.email} → saldo={new_balance}")
    return tx


async def get_balance(db: AsyncSession, user: models.User) -> dict:
    """Retorna saldo + plano + status do user"""
    plan = None
    if user.selected_plan_id:
        res = await db.execute(
            select(models.Plan).where(models.Plan.id == user.selected_plan_id)
        )
        plan = res.scalar_one_or_none()

    return {
        "selected_plan_id": user.selected_plan_id,
        "selected_plan_slug": plan.slug if plan else None,
        "selected_plan_name": plan.name if plan else None,
        "plan_price_brl": float(plan.price_brl) if plan else None,
        "credit_balance": user.credit_balance or 0,
        "credit_status": user.credit_status or "inactive",
        "plan_selected_at": user.plan_selected_at,
        "billing_status": user.billing_status or "billing_not_enabled",
        "credits_last_granted_at": user.credits_last_granted_at,
    }


async def get_transactions(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[list, int]:
    """Lista transações de um user, paginadas (mais recentes primeiro)"""
    from sqlalchemy import func as sqlfunc

    offset = (page - 1) * page_size

    total_res = await db.execute(
        select(sqlfunc.count(models.CreditTransaction.id))
        .where(models.CreditTransaction.user_id == user_id)
    )
    total = total_res.scalar() or 0

    res = await db.execute(
        select(models.CreditTransaction)
        .where(models.CreditTransaction.user_id == user_id)
        .order_by(models.CreditTransaction.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = list(res.scalars().all())
    return items, total
