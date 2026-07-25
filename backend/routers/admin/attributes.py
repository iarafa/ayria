"""
admin/attributes.py — Attribute Definitions (CRUD admin)

Endpoints:
  GET  /attributes  → listar definições ativas
  POST /attributes  → criar nova definição
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


@router.get("/attributes", response_model=list[schemas.AttributeDefinitionResponse])
async def list_attributes(
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Lista definições de atributos"""
    res = await db.execute(
        select(models.AttributeDefinition)
        .where(models.AttributeDefinition.is_active == True)
        .order_by(models.AttributeDefinition.order_index)
    )
    return res.scalars().all()


@router.post("/attributes", response_model=schemas.AttributeDefinitionResponse, status_code=201)
async def create_attribute(
    payload: schemas.AttributeDefinitionCreate,
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Cria novo atributo"""
    existing = await db.execute(
        select(models.AttributeDefinition).where(models.AttributeDefinition.code == payload.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Code já existe")

    attr = models.AttributeDefinition(
        id=uuid.uuid4(),
        code=payload.code,
        label=payload.label,
        description=payload.description,
        attribute_type=payload.attribute_type,
        options=payload.options,
        is_required=payload.is_required,
        is_onboarding=payload.is_onboarding,
        order_index=payload.order_index,
        validation_rules=payload.validation_rules,
        is_active=True,
    )
    db.add(attr)
    await db.commit()
    await db.refresh(attr)
    return attr
