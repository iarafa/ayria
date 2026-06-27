"""
AYRIA - Admin Router
GET    /api/admin/users
GET    /api/admin/knowledge/list
POST   /api/admin/knowledge/upload
DELETE /api/admin/knowledge/{id}
GET    /api/admin/onboarding/config
PUT    /api/admin/onboarding/config
GET    /api/admin/attributes
POST   /api/admin/attributes
PUT    /api/admin/users/{id}/role
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid
import logging

from database import get_db
from utils.security import require_admin
from services.storage_service import storage_service
import models
import schemas

router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = logging.getLogger(__name__)


# ============================================================
# USERS
# ============================================================
@router.get("/users", response_model=list[schemas.AdminUserResponse])
async def list_users(
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os usuários (admin)"""
    res = await db.execute(
        select(models.User).order_by(models.User.created_at.desc())
    )
    users = res.scalars().all()
    
    result = []
    for u in users:
        count_res = await db.execute(
            select(func.count(models.Message.id)).where(models.Message.user_id == u.id)
        )
        count = count_res.scalar() or 0
        result.append(schemas.AdminUserResponse(
            id=u.id, email=u.email, full_name=u.full_name, role=u.role,
            is_active=u.is_active, onboarding_status=u.onboarding_status or "pending",
            created_at=u.created_at, last_login_at=u.last_login_at,
            message_count=count,
        ))
    return result


@router.put("/users/{user_id}/role", response_model=schemas.AdminUserResponse)
async def update_user_role(
    user_id: uuid.UUID,
    payload: schemas.UserRoleUpdate,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Atualiza role de um usuário"""
    res = await db.execute(select(models.User).where(models.User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    user.role = payload.role
    await db.commit()
    await db.refresh(user)
    
    return schemas.AdminUserResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role, is_active=user.is_active,
        onboarding_status=user.onboarding_status or "pending",
        created_at=user.created_at, last_login_at=user.last_login_at,
        message_count=0,
    )


# ============================================================
# ATTRIBUTES
# ============================================================
@router.get("/attributes", response_model=list[schemas.AttributeDefinitionResponse])
async def list_attributes(
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
):
    """Cria novo atributo"""
    # Verifica code duplicado
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


# ============================================================
# ONBOARDING CONFIG
# ============================================================
@router.get("/onboarding/config")
async def get_onboarding_config(
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
):
    """Substitui configuração de onboarding (admin)"""
    # Remove existentes
    await db.execute(models.OnboardingConfig.__table__.delete())
    
    # Insere novos
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


# ============================================================
# KNOWLEDGE DOCUMENTS
# ============================================================
@router.get("/knowledge/list", response_model=list[schemas.KnowledgeDocumentResponse])
async def list_documents(
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lista documentos de conhecimento"""
    res = await db.execute(
        select(models.KnowledgeDocument).order_by(models.KnowledgeDocument.created_at.desc())
    )
    return res.scalars().all()


@router.post("/knowledge/upload", response_model=schemas.KnowledgeDocumentResponse, status_code=201)
async def upload_document(
    title: str = Form(...),
    description: str = Form(None),
    collection: str = Form("conhecimento_geral"),
    file: UploadFile = File(...),
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Upload de documento pra base de conhecimento"""
    # Upload pro storage
    upload_result = await storage_service.upload(file.filename, file.file)
    
    # Cria registro
    doc = models.KnowledgeDocument(
        id=uuid.uuid4(),
        title=title,
        description=description,
        file_name=file.filename,
        file_size_bytes=upload_result["size"],
        storage_url=upload_result["path"],
        storage_provider="local",
        file_hash=upload_result["hash"],
        status="pending",
        chunks_count=0,
        uploaded_by=admin.id,
        collection=collection,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    
    # Em produção: disparar BackgroundTask pra chunking + embedding + Qdrant
    # Por enquanto: marca como "indexed" manualmente
    
    return doc


@router.delete("/knowledge/{doc_id}", status_code=204)
async def delete_document(
    doc_id: uuid.UUID,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Deleta documento"""
    res = await db.execute(
        select(models.KnowledgeDocument).where(models.KnowledgeDocument.id == doc_id)
    )
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    
    # Remove do storage
    if doc.storage_url:
        stored_name = doc.storage_url.split("/")[-1]
        await storage_service.delete(stored_name)
    
    await db.delete(doc)
    await db.commit()
    return None
