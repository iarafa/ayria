"""
AYRIA - Memory Router (Memoria de Longo Prazo)

Endpoints:
GET    /api/memory                  - Lista memorias do user atual
POST   /api/memory                  - Cria memoria manualmente
DELETE /api/memory/{id}             - Deleta memoria
GET    /api/memory/search?q=        - Busca semantica nas memorias
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime
import logging

from database import get_db
from utils.security import get_current_user
from services.vector_service import vector_service
from services.pdf_processor import pdf_processor
import models

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memory", tags=["memory"])


class MemoryCreate(BaseModel):
    text: str
    memory_type: str = "user_fact"  # user_fact, preference, moment, learning
    importance: int = 5  # 1-10
    metadata: Optional[Dict[str, Any]] = None


class MemoryResponse(BaseModel):
    id: str
    text: str
    memory_type: str
    importance: int
    created_at: str
    metadata: Optional[Dict[str, Any]] = None


@router.get("", response_model=List[MemoryResponse])
async def list_memories(
    limit: int = Query(20, le=100),
    memory_type: Optional[str] = None,
    user: models.User = Depends(get_current_user),
):
    """Lista memorias do usuario atual"""
    try:
        results = await vector_service.scroll(
            collection="memoria_episodica",
            user_id=str(user.id),
            memory_type=memory_type,
            limit=limit,
        )
        return [
            MemoryResponse(
                id=r["id"],
                text=r.get("text", ""),
                memory_type=r.get("payload", {}).get("type", "user_fact"),
                importance=r.get("payload", {}).get("importance", 5),
                created_at=r.get("payload", {}).get("created_at", ""),
                metadata=r.get("payload", {}),
            )
            for r in results
        ]
    except Exception as e:
        logger.error(f"Erro listando memorias: {e}")
        return []


@router.post("", response_model=MemoryResponse, status_code=201)
async def create_memory(
    payload: MemoryCreate,
    user: models.User = Depends(get_current_user),
):
    """Cria nova memoria pra o usuario"""
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Texto nao pode ser vazio")

    memory_id = str(uuid.uuid4())
    try:
        embedding = await pdf_processor.generate_embedding(payload.text)
        await vector_service.upsert(
            collection="memoria_episodica",
            point_id=memory_id,
            text=payload.text,
            embedding=embedding,
            payload={
                "user_id": str(user.id),
                "type": payload.memory_type,
                "importance": payload.importance,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "source": "manual",
                **(payload.metadata or {}),
            },
        )
        logger.info(f"✅ Memoria criada: {memory_id} (user={user.email})")
        return MemoryResponse(
            id=memory_id,
            text=payload.text,
            memory_type=payload.memory_type,
            importance=payload.importance,
            created_at=datetime.utcnow().isoformat() + "Z",
            metadata=payload.metadata,
        )
    except Exception as e:
        logger.error(f"Erro criando memoria: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: str,
    user: models.User = Depends(get_current_user),
):
    """Deleta uma memoria"""
    try:
        await vector_service.delete(
            collection="memoria_episodica",
            point_id=memory_id,
            user_id=str(user.id),  # garante que eh do user
        )
        return None
    except Exception as e:
        logger.error(f"Erro deletando memoria: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=List[MemoryResponse])
async def search_memories(
    q: str = Query(..., min_length=1),
    limit: int = Query(5, le=20),
    user: models.User = Depends(get_current_user),
):
    """Busca semantica nas memorias do user"""
    try:
        embedding = await pdf_processor.generate_embedding(q)
        results = await vector_service.search(
            collection="memoria_episodica",
            query_embedding=embedding,
            user_id=str(user.id),
            limit=limit,
        )
        return [
            MemoryResponse(
                id=r["id"],
                text=r.get("text", ""),
                memory_type=r.get("payload", {}).get("type", "user_fact"),
                importance=r.get("payload", {}).get("importance", 5),
                created_at=r.get("payload", {}).get("created_at", ""),
                metadata=r.get("payload", {}),
            )
            for r in results
        ]
    except Exception as e:
        logger.error(f"Erro buscando memorias: {e}")
        return []