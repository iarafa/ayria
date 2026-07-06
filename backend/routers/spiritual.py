"""
AYRIA - Preferência Religiosa/Espiritual do user (Sistema 5)

Permite user escolher orientação religiosa que aparece no header.
- GET  /api/preferences/spiritual           → retorna pref do user atual (ou None)
- POST /api/preferences/spiritual           → cria/atualiza
- DELETE /api/preferences/spiritual         → remove
- GET  /api/preferences/religion-options    → lista de opções disponíveis
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import get_db
from utils.security import get_current_user
import models
import schemas


router = APIRouter(prefix="/api/preferences", tags=["preferences"])


@router.get("/religion-options", response_model=schemas.ReligionOptionsResponse)
async def get_religion_options():
    """Lista de opções religiosas disponíveis pro user escolher."""
    return schemas.ReligionOptionsResponse(
        options=[
            schemas.ReligionOption(value=v, label=l, emoji=e)
            for v, l, e in schemas.RELIGION_OPTIONS
        ]
    )


@router.get("/spiritual", response_model=schemas.SpiritualPreferenceResponse | None)
async def get_spiritual_preference(
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna a preferência religiosa do user atual. None se não respondeu."""
    from sqlalchemy import select as sa_select
    res = await db.execute(
        sa_select(models.SpiritualPreference).where(
            models.SpiritualPreference.user_id == user.id
        )
    )
    pref = res.scalar_one_or_none()
    if not pref:
        return None

    # Resolve o label + emoji pra ficar UI-friendly
    label, emoji = None, None
    for v, l, e in schemas.RELIGION_OPTIONS:
        if v == pref.religion:
            label, emoji = l, e
            break

    return schemas.SpiritualPreferenceResponse(
        user_id=pref.user_id,
        religion=pref.religion,
        religion_label=label or pref.custom_label or pref.religion,
        religion_emoji=emoji or "🙏",
        custom_label=pref.custom_label,
        custom_tags=list(pref.custom_tags or []),
        notes=pref.notes,
        is_active=pref.is_active,
        created_at=pref.created_at,
        updated_at=pref.updated_at,
    )


@router.post("/spiritual", response_model=schemas.SpiritualPreferenceResponse)
async def save_spiritual_preference(
    payload: schemas.SpiritualPreferenceUpdate,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cria ou atualiza a preferência religiosa do user atual."""
    # Validar religion
    valid_keys = {v for v, _, _ in schemas.RELIGION_OPTIONS}
    if payload.religion not in valid_keys:
        raise HTTPException(status_code=400, detail=f"Religion inválida. Opções: {', '.join(sorted(valid_keys))}")

    # Se for 'outro', custom_label é obrigatório
    if payload.religion == "outro" and not (payload.custom_label or "").strip():
        raise HTTPException(status_code=400, detail="Para 'outro', informe custom_label")

    from sqlalchemy import select as sa_select
    res = await db.execute(
        sa_select(models.SpiritualPreference).where(
            models.SpiritualPreference.user_id == user.id
        )
    )
    pref = res.scalar_one_or_none()

    if pref:
        pref.religion = payload.religion
        pref.custom_label = payload.custom_label
        pref.custom_tags = payload.custom_tags or []
        pref.notes = payload.notes
        pref.is_active = payload.is_active
        pref.updated_at = __import__('datetime').datetime.utcnow()
    else:
        pref = models.SpiritualPreference(
            user_id=user.id,
            religion=payload.religion,
            custom_label=payload.custom_label,
            custom_tags=payload.custom_tags or [],
            notes=payload.notes,
            is_active=payload.is_active,
        )
        db.add(pref)

    await db.commit()
    await db.refresh(pref)

    label, emoji = None, None
    for v, l, e in schemas.RELIGION_OPTIONS:
        if v == pref.religion:
            label, emoji = l, e
            break

    return schemas.SpiritualPreferenceResponse(
        user_id=pref.user_id,
        religion=pref.religion,
        religion_label=label or pref.custom_label or pref.religion,
        religion_emoji=emoji or "🙏",
        custom_label=pref.custom_label,
        custom_tags=list(pref.custom_tags or []),
        notes=pref.notes,
        is_active=pref.is_active,
        created_at=pref.created_at,
        updated_at=pref.updated_at,
    )


@router.delete("/spiritual", status_code=204)
async def delete_spiritual_preference(
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a preferência do user (volta pro estado 'não respondeu')."""
    from sqlalchemy import select as sa_select, delete as sa_delete
    res = await db.execute(
        sa_select(models.SpiritualPreference).where(
            models.SpiritualPreference.user_id == user.id
        )
    )
    pref = res.scalar_one_or_none()
    if pref:
        await db.delete(pref)
        await db.commit()
    return None
