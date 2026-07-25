"""
admin/onboarding.py — Onboarding Config (admin)

Endpoints:
  GET /onboarding/config  → retorna config de onboarding
  PUT /onboarding/config  → substitui config inteira
"""
from ._base import (
    APIRouter, Depends,
    select,
    uuid, logging,
    get_db, require_admin,
    models, schemas,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])


@router.get("/onboarding/config")
async def get_onboarding_config(
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Retorna configuração de onboarding"""
    res = await db.execute(
        select(models.OnboardingConfig)
        .order_by(models.OnboardingConfig.step)
    )
    items = res.scalars().all()
    return [
        {
            "id": str(i.id),
            "step": i.step,
            "question_text": i.question_text,
            "helper_text": i.helper_text,
            "question_type": i.question_type,
            "attribute_code": i.attribute_code,
            "options": i.options,
            "is_active": i.is_active,
        }
        for i in items
    ]


@router.put("/onboarding/config")
async def update_onboarding_config(
    items: list[schemas.OnboardingConfigItem],
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Substitui configuração de onboarding (admin)"""
    await db.execute(models.OnboardingConfig.__table__.delete())

    for item in items:
        config = models.OnboardingConfig(
            id=uuid.uuid4(),
            step=item.step,
            question_text=item.question_text,
            helper_text=item.helper_text,
            question_type=item.question_type,
            attribute_code=item.attribute_code,
            options=item.options,
            conditional_show=item.conditional_show,
            is_active=True,
        )
        db.add(config)

    await db.commit()
    return {"updated": len(items)}
