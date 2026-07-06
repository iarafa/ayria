"""
AYRIA - Credits & Plans Router

GET   /api/plans                       — público, lista planos ativos
GET   /api/me/credits                  — saldo + plano do user logado
GET   /api/me/credit-transactions      — histórico paginado
POST  /api/admin/credits/adjust        — admin ajusta saldo manual
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid

from database import get_db
from utils.security import get_current_user, require_admin
import models
import schemas
from services.credit_service import (
    get_balance, get_transactions, admin_adjust_credits,
)

router = APIRouter(tags=["credits"])
# NOTA: o prefix /api é controlado via app.include_router no main.py (se necessário)
# Aqui usamos paths completos pra ficar claro


# ============================================================
# PÚBLICO: listar planos ativos
# ============================================================
@router.get("/api/plans", response_model=list[schemas.PlanResponse])
async def list_plans(db: AsyncSession = Depends(get_db)):
    """Lista planos ativos. Usado pela tela de cadastro."""
    res = await db.execute(
        select(models.Plan)
        .where(models.Plan.active == True)
        .order_by(models.Plan.price_brl.asc())
    )
    plans = res.scalars().all()
    return [
        schemas.PlanResponse(
            id=p.id,
            name=p.name,
            slug=p.slug,
            credits=p.credits,
            price_brl=float(p.price_brl),
            active=p.active,
            created_at=p.created_at,
        )
        for p in plans
    ]


# ============================================================
# USER: saldo + plano
# ============================================================
@router.get("/api/me/credits", response_model=schemas.CreditBalanceResponse)
async def get_my_credits(
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna plano + saldo + status do user logado"""
    return await get_balance(db, user)


# ============================================================
# USER: histórico de transações
# ============================================================
@router.get("/api/me/credit-transactions", response_model=schemas.CreditTransactionListResponse)
async def get_my_credit_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Histórico paginado de movimentações (mais recentes primeiro)"""
    items, total = await get_transactions(db, user.id, page=page, page_size=page_size)
    return schemas.CreditTransactionListResponse(
        items=[
            schemas.CreditTransactionResponse(
                id=t.id,
                type=t.type,
                amount=t.amount,
                balance_before=t.balance_before,
                balance_after=t.balance_after,
                description=t.description,
                reference_type=t.reference_type,
                reference_id=t.reference_id,
                created_at=t.created_at,
            )
            for t in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================================================
# ADMIN: ajustar saldo manual
# ============================================================
@router.post("/api/admin/credits/adjust", response_model=schemas.CreditTransactionResponse)
async def admin_credits_adjust(
    payload: schemas.CreditAdjustRequest,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin adiciona (+) ou remove (-) créditos de um user. Registra em credit_transactions."""
    # Busca user alvo
    target = await db.execute(
        select(models.User).where(models.User.id == payload.user_id)
    )
    target_user = target.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    try:
        tx = await admin_adjust_credits(
            db=db,
            admin_user=admin,
            target_user=target_user,
            amount=payload.amount,
            description=payload.description,
            tx_type=payload.type or "adjustment_manual",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await db.commit()
    await db.refresh(tx)

    return schemas.CreditTransactionResponse(
        id=tx.id,
        type=tx.type,
        amount=tx.amount,
        balance_before=tx.balance_before,
        balance_after=tx.balance_after,
        description=tx.description,
        reference_type=tx.reference_type,
        reference_id=tx.reference_id,
        created_at=tx.created_at,
    )
