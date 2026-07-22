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
from datetime import datetime, timezone
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
    Registra o plano escolhido no cadastro (memória do plano).
    Para planos PAGOS: NÃO credita aqui — crédito vem via webhook Stripe depois do pagamento.
    Idempotente: se user já tem plan_selected_at, não sobrescreve.

    Retorna True se registrou agora, False se já tinha plano.
    """
    # Idempotência: se já tem plano selecionado, não sobrescreve
    if user.selected_plan_id and user.plan_selected_at:
        logger.info(f"Plano já selecionado pro user {user.id} — pulando")
        return False

    # Apenas REGISTRA o plano. NÃO credita créditos — webhook Stripe cuida disso.
    user.selected_plan_id = plan.id
    user.plan_selected_at = datetime.now(timezone.utc)
    # billing_status continua 'billing_not_enabled' até Stripe webhook ativar
    user.billing_status = user.billing_status or "billing_not_enabled"

    logger.info(
        f"✅ Plano registrado no cadastro: user={user.id} plano={plan.slug} "
        f"(créditos virão via webhook Stripe após pagamento)"
    )
    return True


async def consume_credits(
    db: AsyncSession,
    user: models.User,
    amount: int = 1,
    description: Optional[str] = None,
    reference_type: str = "chat_message",
    reference_id: Optional[str] = None,
    action_type_id: Optional[uuid.UUID] = None,
) -> Tuple[bool, Optional[models.CreditTransaction]]:
    """
    Consome créditos. ATÔMICO — bloqueia se saldo insuficiente.

    Regras:
    - Se user.role in (admin, SUPER_ADMIN): bypass total (não consome, não registra)
    - Se onboarding incompleto: bypass (não consome, não registra) — onboarding é grátis
    - Se saldo < amount: retorna (False, None) SEM consumir
    - Caso contrário: desconta + registra transaction

    Novidade (21/07/2026):
    - `action_type_id` referencia a tabela action_types (custo variável: 1/2/5 créditos)
    - description auto-gerado se não informado: "Consumo: <name> (<cost> cr)"
    - credit_transaction guarda action_type_id pra rastreamento

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

    # Se action_type_id foi passado, validar que existe e ajustar amount
    action_name = None
    if action_type_id:
        from sqlalchemy import select
        at_res = await db.execute(
            select(models.ActionType).where(models.ActionType.id == action_type_id)
        )
        at = at_res.scalar_one_or_none()
        if at:
            amount = at.credits_cost  # sobrescreve com o custo do action_type
            action_name = at.name
            logger.debug(f"ActionType '{at.slug}' → custo={amount} cr")

    # Bloqueio por saldo
    if (user.credit_balance or 0) < amount:
        logger.warning(f"❌ User {user.id} sem saldo: {user.credit_balance} < {amount}")
        return False, None

    # Consome (com proteção contra None — 21/07/2026)
    balance_before = user.credit_balance or 0
    user.credit_balance = balance_before - amount
    user.credit_status = "active" if user.credit_balance > 0 else "exhausted"

    # Description auto se não informado
    if not description:
        if action_name:
            description = f"Consumo: {action_name} ({amount} crédito(s))"
        else:
            description = f"Consumo de {amount} crédito(s) por mensagem no chat"

    tx = models.CreditTransaction(
        id=uuid.uuid4(),
        user_id=user.id,
        type="usage_chat_message",
        amount=-amount,  # negativo = consumo
        balance_before=balance_before,
        balance_after=user.credit_balance,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(tx)

    logger.info(
        f"💸 Consumo: user={user.id} -{amount} → saldo={user.credit_balance} "
        f"action={action_name or 'padrão'}"
    )
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
    target_user.credits_last_granted_at = datetime.now(timezone.utc) if amount > 0 else target_user.credits_last_granted_at

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

    # Validação defensiva — 21/07/2026 (evita page negativa ou page_size abusivo)
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
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


# ============================================================
# grant_credits (19/07/2026) — função GENÉRICA pra Stripe webhook
# Concede créditos sem idempotência (pode renovar mensalmente).
# Diferente de grant_initial_credits que só roda 1x.
# ============================================================
async def grant_credits(
    db: AsyncSession,
    user: models.User,
    amount: int,
    description: str,
    reference_type: str = "stripe",
    reference_id: Optional[str] = None,
    plan_slug: Optional[str] = None,  # 🆕 19/07/2026 — associa o plano se user não tiver
) -> int:
    """Concede créditos ao user. Retorna novo saldo.

    🆕 19/07/2026 19:34 — Se plan_slug é passado E user ainda não tem plano,
    o sistema seta `users.selected_plan_id` no user. Garante que o frontend
    sempre saiba qual plano o user comprou (não adivinha dos créditos).
    """
    balance_before = user.credit_balance or 0
    user.credit_balance = balance_before + amount
    user.credit_status = "active" if user.credit_balance > 0 else "exhausted"
    user.credits_last_granted_at = datetime.now(timezone.utc)

    # 🆕 Atalho: associa plano se foi passado
    if plan_slug and user.selected_plan_id is None:
        from sqlalchemy import select
        plan_row = await db.execute(select(models.Plan).where(models.Plan.slug == plan_slug))
        plan_db = plan_row.scalars().first()
        if plan_db:
            user.selected_plan_id = plan_db.id
            logger.info(f"User {user.email} plano setado via grant_credits → {plan_slug}")

    tx = models.CreditTransaction(
        id=uuid.uuid4(),
        user_id=user.id,
        type="grant",
        amount=amount,
        balance_before=balance_before,
        balance_after=user.credit_balance,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id or "",
    )
    db.add(tx)
    logger.info(f"Grant: user={user.id} +{amount} (ref={reference_type}/{reference_id}) → saldo={user.credit_balance}")
    return user.credit_balance
