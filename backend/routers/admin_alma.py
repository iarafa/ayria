"""
AYRIA - Admin Alma Router (08/07/2026)
Endpoints ADMIN p/ gerenciar a SUB-ALMA individual por user.

Plano: 01_Memories/AYRIA_SUB_ALMA_PLANO_08072026.md

# ENDPOINTS (todos admin-only)
# POST /api/admin/users/{user_id}/alma/regenerate  → gera nova draft
# GET  /api/admin/users/{user_id}/alma             → alma ativa + draft pendente
# POST /api/admin/users/{user_id}/alma/approve     → aprova draft → active
# POST /api/admin/users/{user_id}/alma/reject      → rejeita draft → archived
# GET  /api/admin/users/{user_id}/alma/history     → últimas 5 versões
# POST /api/admin/users/{user_id}/alma/rollback/{version}  → volta pra versão X
"""
import uuid
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from utils.security import require_admin
import models
import services.sub_alma_service as sub_alma_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/users", tags=["admin-alma"])


# ============================================================
# SCHEMAS (response shape)
# ============================================================
class AlmaVersionResponse(BaseModel):
    """1 versão de sub-alma serializada."""
    id: str
    version: int
    status: str
    content: str
    signals_used: dict
    trigger: str
    model_used: str
    generated_at: Optional[str] = None
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    created_by: Optional[str] = None
    expires_at: Optional[str] = None

    class Config:
        from_attributes = True


def _serialize(alma: models.UserAlma) -> AlmaVersionResponse:
    return AlmaVersionResponse(
        id=str(alma.id),
        version=alma.version,
        status=alma.status,
        content=alma.content,
        signals_used=alma.signals_used or {},
        trigger=alma.trigger,
        model_used=alma.model_used,
        generated_at=alma.generated_at.isoformat() if alma.generated_at else None,
        approved_at=alma.approved_at.isoformat() if alma.approved_at else None,
        approved_by=str(alma.approved_by) if alma.approved_by else None,
        created_by=str(alma.created_by) if alma.created_by else None,
        expires_at=alma.expires_at.isoformat() if alma.expires_at else None,
    )


class AlmaReadResponse(BaseModel):
    """GET /alma — alma ativa + draft pendente."""
    active: Optional[AlmaVersionResponse] = None
    draft: Optional[AlmaVersionResponse] = None
    has_active: bool
    has_draft: bool


# ============================================================
# ENDPOINTS
# ============================================================
@router.post("/{user_id}/alma/regenerate")
async def regenerate_user_alma(
    user_id: str,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Regenera a sub-alma do user.
    - Cria nova versão em status='draft' (precisa aprovação).
    - Marca a ativa anterior como 'superseded'.
    """
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="user_id inválido")

    try:
        new_alma = await sub_alma_service.generate_user_sub_alma(
            db,
            user_id=uid,
            trigger="admin_manual",
            created_by=admin.id,
            auto_approve=False,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Falha ao regenerar sub-alma do user {uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Falha ao regenerar: {str(e)[:200]}")

    return {
        "ok": True,
        "alma": _serialize(new_alma).model_dump(),
        "message": "Nova versão gerada como DRAFT. Aprove ou rejeite no painel.",
    }


@router.get("/{user_id}/alma", response_model=AlmaReadResponse)
async def get_user_alma(
    user_id: str,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retorna alma ativa + draft pendente."""
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="user_id inválido")

    active = await sub_alma_service.get_user_active_alma(db, uid)
    draft = await sub_alma_service.get_user_draft_alma(db, uid)

    return AlmaReadResponse(
        active=_serialize(active) if active else None,
        draft=_serialize(draft) if draft else None,
        has_active=active is not None,
        has_draft=draft is not None,
    )


@router.post("/{user_id}/alma/approve")
async def approve_user_alma(
    user_id: str,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Aprova draft pendente → vira active. Superseded a anterior."""
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="user_id inválido")

    approved = await sub_alma_service.approve_draft_alma(db, uid, admin.id)
    if not approved:
        raise HTTPException(status_code=404, detail="Nenhuma draft pendente pra aprovar")

    return {
        "ok": True,
        "alma": _serialize(approved).model_dump(),
        "message": f"Sub-alma v{approved.version} aprovada e ativa.",
    }


@router.post("/{user_id}/alma/reject")
async def reject_user_alma(
    user_id: str,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Rejeita draft → archived."""
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="user_id inválido")

    rejected = await sub_alma_service.reject_draft_alma(db, uid, admin.id)
    if not rejected:
        raise HTTPException(status_code=404, detail="Nenhuma draft pendente pra rejeitar")

    return {
        "ok": True,
        "alma": _serialize(rejected).model_dump(),
        "message": f"Sub-alma v{rejected.version} rejeitada (arquivada).",
    }


@router.get("/{user_id}/alma/history")
async def get_user_alma_history(
    user_id: str,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = 5,
):
    """Histórico das últimas N versões (default 5)."""
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="user_id inválido")

    if limit > 20:
        limit = 20

    history = await sub_alma_service.get_user_alma_history(db, uid, limit=limit)
    return {
        "history": [_serialize(a).model_dump() for a in history],
        "total": len(history),
    }


@router.post("/{user_id}/alma/rollback/{version}")
async def rollback_user_alma(
    user_id: str,
    version: int,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Volta a sub-alma pra uma versão específica."""
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="user_id inválido")

    target = await sub_alma_service.rollback_alma(db, uid, version, admin.id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Versão {version} não encontrada")

    return {
        "ok": True,
        "alma": _serialize(target).model_dump(),
        "message": f"Rollback para v{target.version} realizado.",
    }