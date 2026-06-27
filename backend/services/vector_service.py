"""
AYRIA - Vector Service
Integração com Qdrant para as 3 collections:
  - conhecimento_geral (livros/conceitos)
  - memoria_episodica (fatos por user_id)
  - numerologia (interpretações)
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Dict, Optional
import logging
import uuid

from database import settings

logger = logging.getLogger(__name__)


class VectorService:
    """Cliente Qdrant com 3 collections"""
    
    # Embedding dimensions (OpenAI text-embedding-3-small = 1536)
    EMBEDDING_DIM = 1536
    
    COLLECTIONS = {
        "conhecimento_geral": "Livros e conceitos treinados pelo admin",
        "memoria_episodica": "Fatos importantes de cada usuário (por user_id)",
        "numerologia": "Base de interpretações numerológicas",
    }
    
    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
        )
        self._ensure_collections()
    
    def _ensure_collections(self):
        """Cria collections se não existirem"""
        existing = {c.name for c in self.client.get_collections().collections}
        for name in self.COLLECTIONS:
            if name not in existing:
                try:
                    self.client.create_collection(
                        collection_name=name,
                        vectors_config=VectorParams(
                            size=self.EMBEDDING_DIM,
                            distance=Distance.COSINE,
                        ),
                    )
                    logger.info(f"✅ Collection Qdrant criada: {name}")
                except Exception as e:
                    logger.error(f"Erro criando collection {name}: {e}")
    
    async def upsert(
        self,
        collection: str,
        text: str,
        embedding: List[float],
        payload: Dict,
        point_id: Optional[str] = None,
    ):
        """Insere ou atualiza um ponto"""
        if collection not in self.COLLECTIONS:
            raise ValueError(f"Collection inválida: {collection}. Use uma de: {list(self.COLLECTIONS)}")
        
        point = PointStruct(
            id=point_id or str(uuid.uuid4()),
            vector=embedding,
            payload={"text": text, **payload},
        )
        self.client.upsert(collection_name=collection, points=[point])
    
    async def search(
        self,
        collection: str,
        query_embedding: List[float],
        limit: int = 5,
        user_id: Optional[str] = None,
        score_threshold: float = 0.7,
    ) -> List[Dict]:
        """
        Busca semântica.
        Se user_id fornecido em memoria_episodica, filtra por user.
        """
        if collection not in self.COLLECTIONS:
            raise ValueError(f"Collection inválida: {collection}")
        
        query_filter = None
        if collection == "memoria_episodica" and user_id:
            query_filter = Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            )
        
        results = self.client.search(
            collection_name=collection,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
        )
        
        return [
            {"id": r.id, "score": r.score, "text": r.payload.get("text", ""), "payload": r.payload}
            for r in results
        ]
    
    async def delete(self, collection: str, point_id: str):
        """Deleta um ponto"""
        self.client.delete(collection_name=collection, points_selector=[point_id])
    
    async def get_collection_info(self, collection: str) -> Dict:
        """Info da collection"""
        if collection not in self.COLLECTIONS:
            return {"error": f"Collection inválida"}
        info = self.client.get_collection(collection_name=collection)
        return {
            "name": collection,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status,
        }


# Singleton
vector_service = VectorService()
