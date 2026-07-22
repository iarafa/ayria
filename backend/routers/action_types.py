"""
AYRIA — Action Types Admin Router (21/07/2026)
CRUD dos tipos de ação + dashboard de uso de IA.

Endpoints:
- GET    /api/admin/action-types          — lista todos
- POST   /api/admin/action-types          — cria
- GET    /api/admin/action-types/{id}     — detalhe
- PUT    /api/admin/action-types/{id}     — atualiza
- DELETE /api/admin/action-types/{id}     — soft delete (active=false)
- GET    /api/admin/ai-usage/stats        — dashboard custo/tokens
- GET    /api/admin/ai-usage/recent       — últimos N usos
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

import models
import schemas_action_types as schemas
from database import get_db
from utils.security import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin", "action-types"])


# ============================================================
# ACTION TYPES CRUD
# ============================================================

@router.get("/action-types", response_model=List[schemas.ActionTypeResponse])
async def list_action_types(
    active_only: bool = Query(False, description="Se True, só retorna active=true"),
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    """Lista todos os action types (catálogo)."""
    stmt = select(models.ActionType).order_by(models.ActionType.sort_order)
    if active_only:
        stmt = stmt.where(models.ActionType.active == True)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.post("/action-types", response_model=schemas.ActionTypeResponse, status_code=201)
async def create_action_type(
    payload: schemas.ActionTypeCreate,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    """Cria novo action type."""
    # Verifica se slug já existe
    existing = await db.execute(
        select(models.ActionType).where(models.ActionType.slug == payload.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Slug '{payload.slug}' já existe")

    at = models.ActionType(**payload.model_dump())
    db.add(at)
    await db.commit()
    await db.refresh(at)
    logger.info(f"✅ ActionType criado: {at.slug} ({at.credits_cost} cr) por {admin.email}")
    return at


@router.get("/action-types/{action_type_id}", response_model=schemas.ActionTypeResponse)
async def get_action_type(
    action_type_id: str,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    res = await db.execute(
        select(models.ActionType).where(models.ActionType.id == action_type_id)
    )
    at = res.scalar_one_or_none()
    if not at:
        raise HTTPException(status_code=404, detail="ActionType não encontrado")
    return at


@router.put("/action-types/{action_type_id}", response_model=schemas.ActionTypeResponse)
async def update_action_type(
    action_type_id: str,
    payload: schemas.ActionTypeUpdate,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    res = await db.execute(
        select(models.ActionType).where(models.ActionType.id == action_type_id)
    )
    at = res.scalar_one_or_none()
    if not at:
        raise HTTPException(status_code=404, detail="ActionType não encontrado")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(at, field, value)
    await db.commit()
    await db.refresh(at)
    logger.info(f"✅ ActionType atualizado: {at.slug} por {admin.email}")
    return at


@router.delete("/action-types/{action_type_id}", status_code=204)
async def soft_delete_action_type(
    action_type_id: str,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    """Soft delete (active=false) — mantém histórico."""
    res = await db.execute(
        select(models.ActionType).where(models.ActionType.id == action_type_id)
    )
    at = res.scalar_one_or_none()
    if not at:
        raise HTTPException(status_code=404, detail="ActionType não encontrado")
    at.active = False
    await db.commit()
    logger.info(f"🗑️ ActionType desativado: {at.slug} por {admin.email}")


# ============================================================
# AI USAGE DASHBOARD
# ============================================================

@router.get("/ai-usage/stats")
async def ai_usage_stats(
    days: int = Query(30, ge=1, le=365, description="Janela em dias"),
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    """
    Stats agregadas de uso de IA nos últimos N dias:
    - Total de requests
    - Total de tokens (input + output)
    - Custo total em USD e BRL
    - Breakdown por model e por action_type
    """
    since = datetime.utcnow() - timedelta(days=days)

    # Total agregado
    totals_res = await db.execute(
        select(
            func.count(models.AIUsageLog.id).label("total_requests"),
            func.coalesce(func.sum(models.AIUsageLog.prompt_tokens), 0).label("total_input_tokens"),
            func.coalesce(func.sum(models.AIUsageLog.completion_tokens), 0).label("total_output_tokens"),
            func.coalesce(func.sum(models.AIUsageLog.cost_total_usd), 0).label("total_cost_usd"),
            func.count(func.distinct(models.AIUsageLog.user_id)).label("unique_users"),
        ).where(models.AIUsageLog.created_at >= since)
    )
    totals = totals_res.one()

    # Por model
    by_model_res = await db.execute(
        select(
            models.AIUsageLog.model,
            func.count(models.AIUsageLog.id).label("requests"),
            func.coalesce(func.sum(models.AIUsageLog.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(models.AIUsageLog.cost_total_usd), 0).label("cost_usd"),
        ).where(models.AIUsageLog.created_at >= since)
        .group_by(models.AIUsageLog.model)
        .order_by(desc("requests"))
    )
    by_model = [
        {
            "model": row.model,
            "requests": row.requests,
            "tokens": row.tokens,
            "cost_usd": float(row.cost_usd),
        }
        for row in by_model_res.all()
    ]

    # Por action_type (LEFT JOIN pra incluir "sem action_type")
    by_action_res = await db.execute(
        select(
            models.ActionType.slug.label("slug"),
            models.ActionType.name.label("name"),
            func.count(models.AIUsageLog.id).label("requests"),
            func.coalesce(func.sum(models.AIUsageLog.cost_total_usd), 0).label("cost_usd"),
        ).select_from(models.AIUsageLog)
        .outerjoin(models.ActionType, models.AIUsageLog.action_type_id == models.ActionType.id)
        .where(models.AIUsageLog.created_at >= since)
        .group_by(models.ActionType.slug, models.ActionType.name)
        .order_by(desc("requests"))
    )
    by_action = [
        {
            "action_slug": row.slug or "(sem)",
            "action_name": row.name or "Sem action type",
            "requests": row.requests,
            "cost_usd": float(row.cost_usd),
        }
        for row in by_action_res.all()
    ]

    return {
        "window_days": days,
        "since": since.isoformat(),
        "totals": {
            "requests": totals.total_requests,
            "input_tokens": int(totals.total_input_tokens),
            "output_tokens": int(totals.total_output_tokens),
            "total_tokens": int(totals.total_input_tokens + totals.total_output_tokens),
            "cost_usd": float(totals.total_cost_usd),
            "cost_brl": float(totals.total_cost_usd) * 5.0,  # cotação fixa pra simplificar
            "unique_users": totals.unique_users,
        },
        "by_model": by_model,
        "by_action_type": by_action,
    }


@router.get("/ai-usage/recent")
async def ai_usage_recent(
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    """Lista os últimos N usos de IA."""
    res = await db.execute(
        select(models.AIUsageLog).order_by(desc(models.AIUsageLog.created_at)).limit(limit)
    )
    logs = res.scalars().all()
    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "model": log.model,
            "total_tokens": log.total_tokens,
            "cost_usd": float(log.cost_total_usd),
            "response_ms": log.response_ms,
            "status": log.status,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]