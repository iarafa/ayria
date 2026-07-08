"""
AYRIA - Admin User Analysis Router (08/07/2026)
Endpoints ADMIN p/ chat IA trancado num user + persistência de notas.

Plano: 01_Memories/AYRIA_SUB_ALMA_PLANO_08072026.md seção 9B

# ENDPOINTS (todos admin-only)
# POST /api/admin/users/{user_id}/analysis/chat       → bate com a IA focada no user
# POST /api/admin/users/{user_id}/analysis/apply       → salva como nota persistente
# GET  /api/admin/users/{user_id}/analysis/notes       → lista notas do admin
# DELETE /api/admin/users/{user_id}/analysis/notes/{note_id}  → apaga nota
"""
import uuid
import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from utils.security import require_admin
import models
import services.user_analysis_service as user_analysis_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/users", tags=["admin-analysis"])


# ============================================================
# SCHEMAS
# ============================================================
class ChatMsg(BaseModel):
    role: str  # 'user' | 'assistant'
    content: str = Field(min_length=1, max_length=10000)


class ChatRequest(BaseModel):
    messages: List[ChatMsg]


class SaveNoteRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    kind: str = Field(default="analysis")  # analysis|observation|action
    conversation: Optional[List[Dict[str, Any]]] = None
    signals_used: Optional[Dict[str, Any]] = None


class NoteResponse(BaseModel):
    id: str
    user_id: str
    admin_id: str
    admin_email: Optional[str] = None
    kind: str
    title: Optional[str]
    content: str
    conversation: List[Dict[str, Any]]
    model_used: str
    signals_used: Dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


def _serialize_note(note: models.UserSupervisorNote, admin_email: Optional[str] = None) -> NoteResponse:
    return NoteResponse(
        id=str(note.id),
        user_id=str(note.user_id),
        admin_id=str(note.admin_id),
        admin_email=admin_email,
        kind=note.kind,
        title=note.title,
        content=note.content,
        conversation=note.conversation or [],
        model_used=note.model_used,
        signals_used=note.signals_used or {},
        created_at=note.created_at.isoformat() if note.created_at else None,
        updated_at=note.updated_at.isoformat() if note.updated_at else None,
    )


# ============================================================
# ENDPOINTS
# ============================================================
@router.post("/{user_id}/analysis/chat")
async def chat_user_analysis(
    user_id: str,
    payload: ChatRequest,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin conversa com IA focada num user (NÃO consome créditos)."""
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="user_id inválido")

    if not payload.messages:
        raise HTTPException(status_code=400, detail="Mensagens vazias")

    msgs = [{"role": m.role, "content": m.content} for m in payload.messages]

    try:
        result = await user_analysis_service.chat_user_analysis(db, uid, msgs)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Falha no chat de análise do user {uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na IA: {str(e)[:200]}")

    return result


@router.post("/{user_id}/analysis/apply")
async def apply_user_analysis_note(
    user_id: str,
    payload: SaveNoteRequest,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Salva análise/observação/ação do admin sobre um user."""
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="user_id inválido")

    # Garante que user existe
    from sqlalchemy import select as _sel
    user_res = await db.execute(_sel(models.User).where(models.User.id == uid))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User não encontrado")

    note = await user_analysis_service.save_user_supervisor_note(
        db,
        user_id=uid,
        admin_id=admin.id,
        title=payload.title,
        content=payload.content,
        kind=payload.kind,
        conversation=payload.conversation,
        signals_used=payload.signals_used,
    )

    return {
        "ok": True,
        "note": _serialize_note(note, admin_email=admin.email).model_dump(),
        "message": "Nota salva com sucesso.",
    }


@router.get("/{user_id}/analysis/notes")
async def list_user_analysis_notes(
    user_id: str,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
):
    """Lista notas do admin sobre um user."""
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="user_id inválido")

    notes = await user_analysis_service.list_user_supervisor_notes(db, uid, limit=limit)

    # Carrega emails dos admins (pra mostrar quem criou)
    from sqlalchemy import select as _sel
    admin_ids = {n.admin_id for n in notes}
    admin_map: Dict[str, str] = {}
    if admin_ids:
        admins_res = await db.execute(
            _sel(models.User).where(models.User.id.in_(admin_ids))
        )
        for u in admins_res.scalars().all():
            admin_map[str(u.id)] = u.email

    return {
        "notes": [
            _serialize_note(n, admin_email=admin_map.get(str(n.admin_id))).model_dump()
            for n in notes
        ],
        "total": len(notes),
    }


@router.delete("/{user_id}/analysis/notes/{note_id}")
async def delete_user_analysis_note(
    user_id: str,
    note_id: str,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Deleta nota do admin."""
    try:
        uid = uuid.UUID(user_id)
        nid = uuid.UUID(note_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

    # Confere que a nota pertence a esse user
    from sqlalchemy import select as _sel
    note_res = await db.execute(
        _sel(models.UserSupervisorNote).where(
            models.UserSupervisorNote.id == nid,
            models.UserSupervisorNote.user_id == uid,
        )
    )
    note = note_res.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    deleted = await user_analysis_service.delete_user_supervisor_note(db, nid, admin.id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Falha ao deletar")

    return {"ok": True, "deleted_id": str(nid)}