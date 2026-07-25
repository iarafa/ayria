"""
admin/lockouts.py — Login Lockouts (admin gerencia)

Endpoints:
  GET  /login-lockouts        → lista todos os lockouts
  POST /login-lockouts/unlock → admin libera manualmente
"""
from ._base import (
    APIRouter, Depends, HTTPException,
    select,
    datetime, timezone,
    get_db, require_admin,
    models, schemas,
)

router = APIRouter(tags=["admin"])


@router.get("/login-lockouts")
async def list_login_lockouts(
    request = None,
    db=Depends(get_db),
    user: models.User = Depends(require_admin),
):
    """Lista todos os lockouts ativos (e históricos)."""
    res = await db.execute(
        select(models.LoginLockout).order_by(models.LoginLockout.last_failed_at.desc()).limit(200)
    )
    rows = res.scalars().all()
    out = []
    now = datetime.now(timezone.utc)
    for r in rows:
        is_locked = False
        if r.lockout_level >= 5:
            is_locked = True
        elif r.locked_until and r.locked_until > now:
            is_locked = True
        out.append({
            "identifier": r.identifier,
            "identifier_type": r.identifier_type,
            "failed_attempts": r.failed_attempts,
            "locked_until": r.locked_until.isoformat() if r.locked_until else None,
            "lockout_level": r.lockout_level,
            "is_locked": is_locked,
            "label": ["livre","15min","30min","1h","24h","TOTAL"][min(r.lockout_level,5)],
            "last_failed_at": r.last_failed_at.isoformat() if r.last_failed_at else None,
            "unlocked_by": r.unlocked_by,
            "unlocked_at": r.unlocked_at.isoformat() if r.unlocked_at else None,
        })
    return {"items": out, "total": len(out)}


@router.post("/login-lockouts/unlock")
async def unlock_login_lockout(
    payload: schemas.LoginLockoutUnlockRequest,
    request = None,
    db=Depends(get_db),
    user: models.User = Depends(require_admin),
):
    """Admin libera manualmente um lockout."""
    from services.lockout_service import admin_unlock
    ok = await admin_unlock(
        db, payload.identifier, payload.identifier_type, user.email, payload.reason
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Lockout não encontrado")
    return {"ok": True, "identifier": payload.identifier, "unlocked_by": user.email}
