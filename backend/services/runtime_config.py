"""
Runtime config — 19/07/2026.

Permite sobrescrever variáveis do .env em runtime, persistindo em DB.
A tabela `system_config` guarda valores editáveis pelo painel admin.
Em toda leitura (AI_API_KEY, AI_BASE_URL, AI_MODEL, AI_PROVIDER), o código
deve usar este helper: ele busca primeiro no DB, fallback no settings (.env).

Sem cache: cada chamada faz 1 query. Como é só na inicialização ou em endpoint
de status, é aceitável. Se virar gargalo, adicionar cache com TTL de 5s.

Uso:
    from services.runtime_config import rc
    api_key = rc.ai_api_key  # lê DB → fallback settings.AI_API_KEY
"""
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import settings
import models

logger = logging.getLogger(__name__)


class RuntimeConfig:
    """Acesso ao config editável em runtime (DB) com fallback em .env (settings)."""

    # ========== Helpers síncronos (sem DB) — fallback puro ==========
    def _env(self, name: str) -> str:
        return getattr(settings, name, "") or ""

    # ========== Helpers assíncronos (DB) — runtime ==========
    async def _db(self, db: AsyncSession, key: str) -> Optional[str]:
        """Lê 1 chave do DB. Retorna None se não existir."""
        try:
            res = await db.execute(
                select(models.SystemConfig.value).where(models.SystemConfig.key == key)
            )
            row = res.scalar_one_or_none()
            return row
        except Exception as e:
            logger.warning(f"⚠️ Falha ao ler system_config[{key}]: {e}")
            return None

    async def get(self, db: AsyncSession, key: str, default: str = "") -> str:
        """Retorna valor do DB se existir, senão fallback pro default (settings/.env)."""
        val = await self._db(db, key)
        if val is not None and val != "":
            return val
        return self._env(key) if not default else default

    async def set(self, db: AsyncSession, key: str, value: str, updated_by, description: str = "") -> None:
        """Upsert: cria ou atualiza chave."""
        from datetime import datetime
        existing = await db.execute(
            select(models.SystemConfig).where(models.SystemConfig.key == key)
        )
        row = existing.scalar_one_or_none()
        if row:
            row.value = value
            row.updated_by = updated_by
            row.description = description or row.description
        else:
            row = models.SystemConfig(
                key=key, value=value,
                description=description,
                updated_by=updated_by,
            )
            db.add(row)
        await db.commit()
        logger.info(f"✅ system_config[{key}] atualizado por admin {updated_by}")

    async def delete(self, db: AsyncSession, key: str) -> bool:
        """Remove chave do DB (volta pro .env)."""
        existing = await db.execute(
            select(models.SystemConfig).where(models.SystemConfig.key == key)
        )
        row = existing.scalar_one_or_none()
        if row:
            await db.delete(row)
            await db.commit()
            logger.info(f"🗑️ system_config[{key}] removido (volta pro .env)")
            return True
        return False

    async def list_all(self, db: AsyncSession) -> dict[str, str]:
        """Lista todas as chaves do DB."""
        res = await db.execute(select(models.SystemConfig.key, models.SystemConfig.value))
        return {k: v for k, v in res.all()}

    # ========== Atalho: AI config ==========
    async def ai_config(self, db: AsyncSession) -> dict:
        """Retorna config de IA completa (DB overrides .env)."""
        api_key = await self.get(db, "AI_API_KEY", self._env("AI_API_KEY"))
        base_url = await self.get(db, "AI_BASE_URL", self._env("AI_BASE_URL"))
        model = await self.get(db, "AI_MODEL", self._env("AI_MODEL"))
        provider = await self.get(db, "AI_PROVIDER", self._env("AI_PROVIDER") or "MiniMax")
        return {
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "provider": provider,
            "api_key_set": bool(api_key),
            "configured": bool(api_key and base_url),
        }


# Singleton
rc = RuntimeConfig()