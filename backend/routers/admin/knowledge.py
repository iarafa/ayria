"""
admin/knowledge.py — Knowledge Documents

Endpoints:
  GET    /knowledge/list       → listar documentos
  POST   /knowledge/upload      → upload (com background processing)
  DELETE /knowledge/{doc_id}    → deletar (Qdrant + storage + DB)
"""
from ._base import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks,
    select,
    uuid, logging, datetime,
    get_db, require_admin,
    storage_service, models, schemas,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])


@router.get("/knowledge/list", response_model=list[schemas.KnowledgeDocumentResponse])
async def list_documents(
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
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
    db=Depends(get_db),
):
    """Upload de documento pra base de conhecimento"""
    ALLOWED_TYPES = {
        "application/pdf",
        "text/plain",
        "text/markdown",
        "text/x-markdown",
        "text/html",
    }
    if not file.content_type or file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de arquivo não permitido ({file.content_type}). Aceitos: PDF, TXT, MD, HTML."
        )

    MAX_SIZE = 50 * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo muito grande ({len(file_bytes) // (1024*1024)}MB). Máximo: 50MB."
        )

    if file.filename and (".." in file.filename or "/" in file.filename or "\\" in file.filename):
        raise HTTPException(
            status_code=400,
            detail="Nome de arquivo inválido (não pode ter / ou ..)."
        )

    collection_folder = f"knowledge/{collection}" if collection else "knowledge"
    upload_result = await storage_service.upload(
        file_bytes=file_bytes,
        filename=file.filename,
        content_type=file.content_type,
        folder=collection_folder,
    )

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
    db=Depends(get_db),
):
    """Deleta documento de conhecimento E TODOS os vestígios:
    1. Qdrant: TODOS os chunks indexados
    2. Azure Blob / Storage local: arquivo original
    3. PostgreSQL: registro
    """
    res = await db.execute(
        select(models.KnowledgeDocument).where(models.KnowledgeDocument.id == doc_id)
    )
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    deleted_summary = {"qdrant_chunks": 0, "storage": False}

    try:
        from services.vector_service import vector_service
        deleted_summary["qdrant_chunks"] = await vector_service.delete_document_chunks(str(doc_id))

        if doc.storage_url:
            storage_deleted = await storage_service.delete(doc.storage_url)
            deleted_summary["storage"] = storage_deleted

        await db.delete(doc)
        await db.commit()

        logger.info(
            f"✅ Documento '{doc.file_name}' ({doc_id}) excluído COMPLETAMENTE por admin {admin.email}. "
            f"Chunks Qdrant: {deleted_summary['qdrant_chunks']}, Storage: {deleted_summary['storage']}"
        )
        return None

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Erro ao excluir documento {doc_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao excluir documento. Tente novamente."
        )
