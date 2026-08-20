"""
AYRIA - Embedding Cache (camada 1 de proteção do Qdrant)

Cache em memória pra evitar chamadas idênticas ao Qdrant em sequência.
Em pico (100 user), muitas queries são repetidas (ex: "o que é numerologia?").

- TTL: 60 segundos (queries mudam pouco em janelas curtas)
- Limite: 256 entradas (LRU eviction)
- Thread-safe (asyncio.Lock)
"""
import asyncio
import hashlib
import time
from collections import OrderedDict
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """LRU cache em memória pra queries do Qdrant."""

    def __init__(self, max_size: int = 256, ttl_seconds: int = 60):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0

    def _key(self, query: str, collection: str, user_id: Optional[str], limit: int) -> str:
        """Gera chave única baseada nos parâmetros."""
        raw = f"{collection}|{user_id or 'anon'}|{limit}|{query.strip().lower()}"
        return hashlib.md5(raw.encode()).hexdigest()

    async def get(
        self,
        query: str,
        collection: str,
        user_id: Optional[str],
        limit: int,
    ) -> Optional[List[Dict]]:
        """Busca no cache. Retorna None se miss/expirado."""
        async with self._lock:
            key = self._key(query, collection, user_id, limit)
            if key not in self._cache:
                self.misses += 1
                return None
            ts, value = self._cache[key]
            if time.time() - ts > self.ttl:
                del self._cache[key]
                self.misses += 1
                return None
            # Hit: move pro fim (LRU)
            self._cache.move_to_end(key)
            self.hits += 1
            logger.debug(f"🎯 Cache HIT: {collection} (rate: {self.hit_rate():.1%})")
            return value

    async def set(
        self,
        query: str,
        collection: str,
        user_id: Optional[str],
        limit: int,
        value: List[Dict],
    ) -> None:
        """Guarda no cache (eviction LRU se cheio)."""
        async with self._lock:
            key = self._key(query, collection, user_id, limit)
            self._cache[key] = (time.time(), value)
            self._cache.move_to_end(key)
            # Eviction se passou do limite
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)  # remove oldest

    def hit_rate(self) -> float:
        """Taxa de acerto do cache."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def stats(self) -> Dict[str, Any]:
        """Stats pra dashboard."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{self.hit_rate():.1%}",
        }


# Singleton global
embedding_cache = EmbeddingCache(max_size=256, ttl_seconds=60)
