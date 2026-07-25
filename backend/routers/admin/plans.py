"""
admin/plans.py — CRUD de planos comerciais

Endpoints:
  GET /plans           → listar todos (incluindo inativos)
  PUT /plans/{plan_id} → editar (NÃO muda slug)
"""
from ._base import (
    APIRouter, Depends, HTTPException,
    select,
    uuid, logging,
    get_db, require_admin,
    models, schemas,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])


@router.get("/plans", response_model=list[schemas.PlanResponse])
async def list_plans_admin(
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Lista TODOS os planos (incluindo inativos)."""
    res = await db.execute(select(models.Plan).order_by(models.Plan.credits))
    return res.scalars().all()


@router.put("/plans/{plan_id}", response_model=schemas.PlanResponse)
async def update_plan(
    plan_id: uuid.UUID,
    payload: schemas.AdminPlanUpdate,
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Admin edita um plano existente. NÃO permite mudar slug (identidade).

    IMPORTANTE: editar credits NÃO altera saldos de usuários existentes -
    só afeta novos cadastros.
    """
    res = await db.execute(select(models.Plan).where(models.Plan.id == plan_id))
    plan = res.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    if payload.name is not None:
        plan.name = payload.name
    if payload.credits is not None:
        plan.credits = payload.credits
    if payload.price_brl is not None:
        plan.price_brl = payload.price_brl
    if payload.active is not None:
        plan.active = payload.active

    await db.commit()
    await db.refresh(plan)
    return plan
