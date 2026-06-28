"""
AYRIA - Training Router (Modulo Treinamento do Admin)

Endpoints pra admin verificar status do RAG/conhecimento:
GET    /api/admin/training/status         - Status geral (collections, contadores)
GET    /api/admin/training/conhecimento   - Lista chunks indexados em conhecimento_geral
POST   /api/admin/training/test-search    - Testa busca semantica
POST   /api/admin/training/reindex/{id}   - Re-indexa documento
DELETE /api/admin/training/chunk/{id}     - Deleta chunk especifico
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime
import logging

from database import get_db
from utils.security import require_admin
from services.vector_service import vector_service
from services.pdf_processor import pdf_processor
import models

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/training", tags=["training"])


@router.get("/status")
async def training_status(
    admin: models.User = Depends(require_admin),
):
    """Status geral do sistema de treinamento/RAG"""
    status = {
        "collections": {},
        "ai_service": "minimax",
        "embedding_dim": pdf_processor.embedding_dim,
        "chunk_size": pdf_processor.chunk_size,
    }
    for coll in vector_service.COLLECTIONS:
        try:
            info = await vector_service.get_collection_info(coll)
            status["collections"][coll] = info
        except Exception as e:
            status["collections"][coll] = {"error": str(e)}
    return status


@router.get("/conhecimento")
async def list_conhecimento(
    limit: int = Query(50, le=200),
    document_id: Optional[str] = None,
    admin: models.User = Depends(require_admin),
):
    """Lista chunks indexados na base de conhecimento geral"""
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    conditions = []
    if document_id:
        conditions.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))

    qfilter = Filter(must=conditions) if conditions else None

    try:
        results, total = vector_service.client.scroll(
            collection_name="conhecimento_geral",
            scroll_filter=qfilter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return {
            "total": total,
            "returned": len(results),
            "chunks": [
                {
                    "id": str(p.id),
                    "text": (p.payload or {}).get("text", ""),
                    "text_preview": (p.payload or {}).get("text_preview", ""),
                    "document_id": (p.payload or {}).get("document_id"),
                    "file_name": (p.payload or {}).get("file_name"),
                    "chunk_index": (p.payload or {}).get("chunk_index", 0),
                    "extracted_at": (p.payload or {}).get("extracted_at"),
                }
                for p in results
            ],
        }
    except Exception as e:
        logger.error(f"Erro listando conhecimento: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TestSearchRequest(BaseModel):
    query: str
    limit: int = 5
    collection: str = "conhecimento_geral"


@router.post("/test-search")
async def test_search(
    payload: TestSearchRequest,
    admin: models.User = Depends(require_admin),
):
    """Admin testa busca semantica pra ver se o RAG ta funcionando"""
    try:
        embedding = await pdf_processor.generate_embedding(payload.query)
        results = await vector_service.search(
            collection=payload.collection,
            query_embedding=embedding,
            limit=payload.limit,
            score_threshold=0.0,
        )
        return {
            "query": payload.query,
            "collection": payload.collection,
            "results": [
                {
                    "id": r["id"],
                    "score": r.get("score", 0),
                    "text": r.get("text", "")[:300],
                    "file_name": r.get("payload", {}).get("file_name"),
                    "chunk_index": r.get("payload", {}).get("chunk_index"),
                }
                for r in results
            ],
        }
    except Exception as e:
        logger.error(f"Erro test-search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reindex/{doc_id}")
async def reindex_document(
    doc_id: str,
    background_tasks: BackgroundTasks,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Re-indexa um documento (deleta chunks antigos e reprocessa)"""
    doc_res = await db.execute(
        select(models.KnowledgeDocument).where(models.KnowledgeDocument.id == uuid.UUID(doc_id))
    )
    doc = doc_res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")

    # Marca como reindexing
    doc.status = "reindexing"
    await db.commit()

    # Deletar chunks antigos do Qdrant
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    try:
        vector_service.client.delete(
            collection_name=doc.collection,
            points_selector=Filter(must=[
                FieldCondition(key="document_id", match=MatchValue(value=str(doc.id)))
            ]),
        )
    except Exception as e:
        logger.warning(f"Erro deletando chunks antigos: {e}")

    # Re-baixar arquivo do Azure/local
    try:
        import httpx
        if doc.storage_url and doc.storage_url.startswith("http"):
            async with httpx.AsyncClient() as client:
                resp = await client.get(doc.storage_url)
                file_bytes = resp.content
        else:
            with open(doc.storage_url, "rb") as f:
                file_bytes = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao baixar arquivo: {e}")

    # Background: reprocessar
    background_tasks.add_task(
        reindex_background,
        doc_id=str(doc.id),
        file_bytes=file_bytes,
        file_name=doc.file_name,
        collection=doc.collection,
    )

    return {"status": "reindexing", "doc_id": str(doc.id)}


async def reindex_background(doc_id, file_bytes, file_name, collection):
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
                doc.status = "indexed" if result.get("errors", 0) == 0 else "failed"
                doc.chunks_count = result.get("indexed", 0)
                doc.indexed_at = datetime.utcnow()
                await db.commit()
    except Exception as e:
        logger.error(f"Erro reindex background: {e}")


@router.delete("/chunk/{chunk_id}")
async def delete_chunk(
    chunk_id: str,
    admin: models.User = Depends(require_admin),
):
    """Deleta um chunk especifico do Qdrant"""
    try:
        vector_service.client.delete(
            collection_name="conhecimento_geral",
            points_selector=[chunk_id],
        )
        return {"deleted": chunk_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))