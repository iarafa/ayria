"""
AYRIA - Admin Router
GET    /api/admin/users
POST   /api/admin/users            - Cria user (admin pode passar role=admin)
PUT    /api/admin/users/{id}        - Edita nome / is_active
DELETE /api/admin/users/{id}        - Exclui user
GET    /api/admin/knowledge/list
POST   /api/admin/knowledge/upload
DELETE /api/admin/knowledge/{id}
GET    /api/admin/onboarding/config
PUT    /api/admin/onboarding/config
GET    /api/admin/attributes
POST   /api/admin/attributes
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid
import logging
from datetime import datetime

from database import get_db
from utils.security import require_admin, hash_password
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


@router.post("/users", response_model=schemas.AdminUserResponse, status_code=201)
async def create_user(
    payload: schemas.UserRegister,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin cria novo usuário. Pode passar role=SUPER_ADMIN no payload se quiser criar admin."""
    existing = await db.execute(
        select(models.User).where(models.User.email == payload.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    # Admin pode escolher role no momento da criação
    requested_role = getattr(payload, "role", "user")
    if requested_role not in ("user", "SUPER_ADMIN"):
        requested_role = "user"

    user = models.User(
        id=uuid.uuid4(),
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=requested_role,  # Admin define role direto na criação (sem promoção depois)
        is_active=True,
        is_verified=True,  # Admin cria já verificado
        onboarding_status="pending",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return schemas.AdminUserResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role, is_active=user.is_active,
        onboarding_status=user.onboarding_status or "pending",
        created_at=user.created_at, last_login_at=user.last_login_at,
        message_count=0,
    )


@router.put("/users/{user_id}", response_model=schemas.AdminUserResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: schemas.UserUpdate,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Edita nome e/ou is_active de um usuário (NÃO muda role)."""
    res = await db.execute(select(models.User).where(models.User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Você não pode editar a si mesmo")

    # Editar apenas campos permitidos (NÃO role)
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active

    await db.commit()
    await db.refresh(user)

    return schemas.AdminUserResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role, is_active=user.is_active,
        onboarding_status=user.onboarding_status or "pending",
        created_at=user.created_at, last_login_at=user.last_login_at,
        message_count=0,
    )


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Exclui um usuário E TODOS os dados dele (LGPD-style):
    - PostgreSQL: user_profiles, user_attributes, chats, messages
    - Qdrant: TODAS as memórias (memoria_episodica)
    - Audit log: preservado mas com user_id=NULL (pra auditoria)
    - Knowledge documents: NÃO deleta (são do admin, não do user)

    Safety:
    - Admin não pode excluir a si mesmo
    - Operação atômica — se algo falhar, ROLLBACK
    """
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir a si mesmo")

    res = await db.execute(select(models.User).where(models.User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    deleted_summary = {"pg": {}, "qdrant": 0}

    try:
        from sqlalchemy import text

        # 1. PostgreSQL: user_profiles (1:1)
        r = await db.execute(text("DELETE FROM user_profiles WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["user_profiles"] = r.rowcount

        # 2. PostgreSQL: user_attributes (valores dos atributos)
        r = await db.execute(text("DELETE FROM user_attributes WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["user_attributes"] = r.rowcount

        # 3. PostgreSQL: messages (via chats)
        r = await db.execute(text("DELETE FROM messages WHERE chat_id IN (SELECT id FROM chats WHERE user_id = :uid)"), {"uid": str(user_id)})
        deleted_summary["pg"]["messages"] = r.rowcount

        # 4. PostgreSQL: chats
        r = await db.execute(text("DELETE FROM chats WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["chats"] = r.rowcount

        # 5. Audit log: NULL user_id (preserva histórico, mas sem FK)
        # Não deleta — auditoria deve permanecer (LGPD permite pra fins de segurança)
        r = await db.execute(text("UPDATE audit_log SET user_id = NULL WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["audit_log_anonymized"] = r.rowcount

        # 6. Qdrant: TODAS as memórias do user
        from services.vector_service import vector_service
        deleted_summary["qdrant"] = await vector_service.delete_user_memories(str(user_id))

        # 7. Finalmente: deleta o user
        await db.delete(user)
        await db.commit()

        logger.info(
            f"✅ User {user.email} ({user_id}) excluído COMPLETAMENTE por admin {admin.email}. "
            f"Postgres: {deleted_summary['pg']}, Qdrant collections: {deleted_summary['qdrant']}"
        )
        return None

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Erro ao excluir user {user.email}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao excluir usuário (rollback feito): {str(e)}"
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
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: str = Form(None),
    collection: str = Form("conhecimento_geral"),
    file: UploadFile = File(...),
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Upload de documento pra base de conhecimento"""
    # Upload pro storage
    file_bytes = await file.read()
    upload_result = await storage_service.upload(
        file_bytes=file_bytes,
        filename=file.filename,
        content_type=file.content_type,
    )
    
    # Cria registro
    doc = models.KnowledgeDocument(
        id=uuid.uuid4(),
        title=title,
        description=description,
        file_name=file.filename,
        file_size_bytes=upload_result["size_bytes"],
        storage_url=upload_result["url"],
        storage_provider=upload_result["storage"],
        file_hash=upload_result.get("hash", ""),
        status="pending",
        chunks_count=0,
        uploaded_by=admin.id,
        collection=collection,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # REAL: dispara BackgroundTask pra chunking + embedding + Qdrant
    background_tasks.add_task(
        process_document_background,
        doc_id=str(doc.id),
        file_bytes=file_bytes,
        file_name=file.filename,
        collection=collection,
        db_url=str(db.bind.url) if db.bind else "",
    )

    logger.info(f"📚 Doc '{title}' salvo ({len(file_bytes)} bytes) - indexação em background")

    return doc


async def process_document_background(
    doc_id: str,
    file_bytes: bytes,
    file_name: str,
    collection: str,
    db_url: str,
):
    """Background: chunking + embedding + Qdrant"""
    from services.pdf_processor import pdf_processor
    from database import AsyncSessionLocal

    try:
        result = await pdf_processor.process_pdf(
            file_bytes=file_bytes,
            file_name=file_name,
            document_id=doc_id,
            collection=collection,
        )

        # Atualiza status no DB
        async with AsyncSessionLocal() as db:
            doc_res = await db.execute(
                select(models.KnowledgeDocument).where(models.KnowledgeDocument.id == uuid.UUID(doc_id))
            )
            doc = doc_res.scalar_one_or_none()
            if doc:
                if result.get("errors", 0) == 0 and result.get("indexed", 0) > 0:
                    doc.status = "indexed"
                    doc.chunks_count = result["indexed"]
                    doc.indexed_at = datetime.utcnow()
                else:
                    doc.status = "failed"
                    doc.error_message = f"{result.get('errors', 0)} erros no processamento"
                await db.commit()

        logger.info(f"✅ Background processado: doc {doc_id} status={doc.status if doc else 'unknown'}")
    except Exception as e:
        logger.error(f"❌ Erro no background processing: {e}", exc_info=True)
        # Marca como failed
        try:
            async with AsyncSessionLocal() as db:
                doc_res = await db.execute(
                    select(models.KnowledgeDocument).where(models.KnowledgeDocument.id == uuid.UUID(doc_id))
                )
                doc = doc_res.scalar_one_or_none()
                if doc:
                    doc.status = "failed"
                    doc.error_message = str(e)[:500]
                    await db.commit()
        except Exception:
            pass


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
