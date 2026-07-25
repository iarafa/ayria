"""
admin/audit.py — Audit log + ingest de logs do frontend

Endpoints:
  GET  /audit/recent  → últimos audit_logs (admin only)
  POST /log/event     → recebe evento de erro do frontend
"""
from ._base import (
    APIRouter, Depends, HTTPException, Request,
    select, BaseModel,
    uuid, logging, datetime, timezone, Optional, json,
    get_db, require_admin,
    models,
)
import traceback as _tb

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])


@router.get("/audit/recent", response_model=list[dict])
async def list_recent_audit_logs(
    limit: int = 100,
    user_id: Optional[uuid.UUID] = None,
    action_filter: Optional[str] = None,
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Lista últimos audit_logs pra investigar incidentes.
    Filtros opcionais: user_id, action_filter (substring)."""
    from models import AuditLog

    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 500))
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action_filter:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action_filter}%"))

    res = await db.execute(stmt)
    logs = res.scalars().all()

    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "ip_address": str(log.ip_address) if log.ip_address else None,
            "user_agent": (log.user_agent or "")[:200],
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ============================================================
# FRONTEND ERROR INGEST — recebe erros do frontend e grava no log
# ============================================================
_frontend_logger = logging.getLogger("ayria.frontend")


class FrontendLogEvent(BaseModel):
    """Evento de erro reportado pelo frontend."""
    level: str = "error"  # error | warn | info
    source: Optional[str] = None  # ex: "AdminPage", "ChatPage"
    context: Optional[str] = None  # ex: "loadUsers", "sendMessage"
    message: str
    data: Optional[dict] = None
    url: Optional[str] = None
    user_agent: Optional[str] = None


@router.post("/log/event", status_code=201)
async def ingest_frontend_log(
    event: FrontendLogEvent,
    request: Request,
    admin: models.User = Depends(require_admin),
):
    """Recebe evento de erro do frontend e grava no log do backend."""
    ip = request.client.host if request.client else "?"
    payload = {
        "source": event.source,
        "context": event.context,
        "message": event.message,
        "data": event.data,
        "url": event.url,
        "ip": ip,
        "user_agent": event.user_agent,
    }
    msg = f"[FRONTEND] {event.source or '?'}/{event.context or '?'} | {event.message}"

    if event.level == "error":
        _frontend_logger.error("%s | %s", msg, json.dumps(payload, ensure_ascii=False, default=str))
    elif event.level == "warn":
        _frontend_logger.warning("%s | %s", msg, json.dumps(payload, ensure_ascii=False, default=str))
    else:
        _frontend_logger.info("%s | %s", msg, json.dumps(payload, ensure_ascii=False, default=str))

    return {"ok": True, "logged": event.level}
