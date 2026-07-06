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
        # Lazy init: só tenta conectar quando precisar
        self._initialized = False

    def _ensure_init(self):
        """Inicializa collections na primeira chamada. Falha silenciosa."""
        if not self._initialized:
            try:
                self._ensure_collections()
                self._initialized = True
            except Exception as e:
                logger.warning(
                    f"Qdrant indisponível em {settings.QDRANT_URL}: {e}. "
                    "RAG ficará degradado até Qdrant subir."
                )
    
    def _ensure_collections(self):
        """Cria collections se não existirem. Chamado por _ensure_init()."""
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
        self._ensure_init()

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
        self._ensure_init()
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
    
    async def delete(self, collection: str, point_id: str, user_id: Optional[str] = None):
        """Deleta um ponto"""
        self.client.delete(collection_name=collection, points_selector=[point_id])

    async def delete_user_memories(self, user_id: str) -> int:
        """
        Deleta TODAS as memórias de um usuário em todas as coleções que têm user_id.
        Usado quando user é excluído (LGPD-style).

        Returns: número de pontos deletados.
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        qfilter = Filter(must=[
            FieldCondition(key="user_id", match=MatchValue(value=str(user_id)))
        ])

        total_deleted = 0
        for collection_name in self.COLLECTIONS.keys():
            try:
                # Verifica se coleção existe antes de tentar deletar
                collections = self.client.get_collections().collections
                exists = any(c.name == collection_name for c in collections)
                if not exists:
                    continue

                # Deleta por filtro
                self.client.delete(
                    collection_name=collection_name,
                    points_selector=qfilter,
                )
                logger.info(f"🗑️ User memories deletadas de {collection_name} para user {user_id}")
                total_deleted += 1  # incrementa por coleção processada
            except Exception as e:
                logger.warning(f"Falha ao deletar memories de {collection_name} para user {user_id}: {e}")
                continue

        return total_deleted

    async def delete_document_chunks(self, document_id: str) -> int:
        """
        Deleta TODOS os chunks de um documento da coleção conhecimento_geral.
        Usado quando admin deleta um knowledge document.

        Returns: número de pontos deletados.
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        qfilter = Filter(must=[
            FieldCondition(key="document_id", match=MatchValue(value=str(document_id)))
        ])

        try:
            # Verifica se coleção existe
            collections = self.client.get_collections().collections
            if not any(c.name == "conhecimento_geral" for c in collections):
                return 0

            # Conta antes pra logar
            before = self.client.count(
                collection_name="conhecimento_geral",
                count_filter=qfilter,
            ).count

            # Deleta
            self.client.delete(
                collection_name="conhecimento_geral",
                points_selector=qfilter,
            )
            logger.info(f"🗑️ Deletados {before} chunks do documento {document_id} do Qdrant")
            return before
        except Exception as e:
            logger.warning(f"Falha ao deletar chunks do documento {document_id}: {e}")
            return 0

    async def scroll(
        self,
        collection: str,
        user_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """Lista pontos com filtros"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        conditions = []
        if user_id:
            conditions.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))
        if memory_type:
            conditions.append(FieldCondition(key="type", match=MatchValue(value=memory_type)))

        qfilter = Filter(must=conditions) if conditions else None

        results, _ = self.client.scroll(
            collection_name=collection,
            scroll_filter=qfilter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        out = []
        for point in results:
            out.append({
                "id": str(point.id),
                "payload": dict(point.payload or {}),
                "text": (point.payload or {}).get("text", ""),
            })
        return out
    
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
