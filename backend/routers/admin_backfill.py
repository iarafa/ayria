"""
AYRIA - Admin Backfill Router (08/07/2026)
End-point único p/ backfill inicial de sub-almas.
SKIP admin (admin@ayria.local e SUPER_ADMIN — eles são o sistema).
"""
import time
import datetime as _dt
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from utils.security import require_admin
import models
import services.sub_alma_service as sub_alma_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/almas", tags=["admin-backfill"])


@router.post("/backfill-all")
async def backfill_all_user_almas(
    request: Request,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Gera sub-alma inicial pra todos users existentes que AINDA não têm.

    - SKIP admin (role != 'user') — admin não precisa de sub-alma individual.
    - SKIP quem já tem sub-alma ATIVA (idempotente — pode rodar de novo).
    - SKIP quem não completou onboarding.
    - trigger='backfill_initial', auto_approve=True (alma inicial vai direto pra active —
      é rascunho, não vale a pena admin aprovar 18 uma por uma).
    - CADA GERAÇÃO LEVA ~10-15s (chamada IA). Pra 18 users, ~3-4min total.
      Endpoint é SÍNCRONO. UI mostra "gerando..." enquanto.
    """
    users_res = await db.execute(
        select(models.User).where(
            models.User.role == "user",
            models.User.onboarding_status == "completed",
        )
    )
    candidates = list(users_res.scalars().all())

    # Filtra quem NÃO tem sub-alma ativa (idempotência)
    eligible = []
    for u in candidates:
        existing = await sub_alma_service.get_user_active_alma(db, u.id)
        if not existing:
            eligible.append(u)

    results = {
        "total_users_with_onboarding": len(candidates),
        "already_has_alma": len(candidates) - len(eligible),
        "to_generate": len(eligible),
        "generated_ok": 0,
        "failed": 0,
        "errors": [],
        "started_at": None,
        "duration_seconds": None,
        "triggered_by": admin.email,
    }

    started_at = _dt.datetime.now(_dt.timezone.utc)
    results["started_at"] = started_at.isoformat()
    t0 = time.time()

    logger.info(f"🔄 Backfill sub-almas iniciado: {len(eligible)} users (admin: {admin.email})")

    for u in eligible:
        try:
            await sub_alma_service.generate_user_sub_alma(
                db,
                user_id=u.id,
                trigger="backfill_initial",
                created_by=None,  # auto (não é manual admin)
                auto_approve=True,  # backfill inicial: direto pra active
            )
            results["generated_ok"] += 1
            logger.info(f"   ✅ {u.email} (v1, active)")
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({
                "user_id": str(u.id),
                "email": u.email,
                "error": str(e)[:150],
            })
            logger.error(f"   ❌ {u.email}: {e}")

    results["duration_seconds"] = round(time.time() - t0, 1)
    logger.info(
        f"🏁 Backfill finalizado: {results['generated_ok']} ok, "
        f"{results['failed']} falhas em {results['duration_seconds']}s"
    )
    return results
