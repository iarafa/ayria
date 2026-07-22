"""
AYRIA - AI Service
APENAS MiniMax (regra absoluta do sistema). OpenAI foi REMOVIDO COMPLETAMENTE.

19/07/2026: Settings lidas em RUNTIME via `runtime_config.rc`, não mais do `.env` direto.
Permite editar pelo painel admin (aba Configurações) sem reiniciar backend.
"""
from typing import List, Dict, Optional
from openai import AsyncOpenAI
import logging

from database import settings
from services.runtime_config import rc
import models

logger = logging.getLogger(__name__)


class AIService:
    """Cliente IA: APENAS MiniMax via AI_BASE_URL."""

    def __init__(self):
        # Fallback inicial (DB lido a cada chamada, ver `_resolve_config`)
        self.model = settings.AI_MODEL
        self.base_url = settings.AI_BASE_URL
        self.provider = "MiniMax"
        self.client: Optional[AsyncOpenAI] = None
        self._init_client(self.base_url, settings.AI_API_KEY)

    def _init_client(self, base_url: str, api_key: str):
        """(Re)inicializa o cliente OpenAI-compat com as credenciais atuais."""
        self.base_url = base_url
        if not api_key:
            logger.warning(
                "⚠️ AI_API_KEY não configurada. Defina em Configurações (admin) ou no .env"
            )
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
            )
            logger.info(
                f"✅ AI client inicializado: {base_url} | model={self.model}"
            )

    async def _resolve_config(self) -> dict:
        """Lê config do DB (sobrescreve .env). Se mudou, rebuilda client."""
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            cfg = await rc.ai_config(db)
        if (
            cfg["base_url"] != self.base_url
            or cfg["model"] != self.model
            or cfg["provider"] != self.provider
        ):
            self.model = cfg["model"]
            self.provider = cfg["provider"]
            self._init_client(cfg["base_url"], cfg["api_key"])
        return cfg

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        """Envia mensagem pra MiniMax."""
        # Resolve config em runtime (DB > .env)
        cfg = await self._resolve_config()
        if not cfg["api_key"]:
            raise RuntimeError(
                "AI não configurada. Defina em Configurações (admin) ou no .env (MiniMax)"
            )
        if not self.client or cfg["base_url"] != self.base_url:
            self._init_client(cfg["base_url"], cfg["api_key"])

        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp
        except Exception as e:
            logger.error(f"❌ MiniMax falhou: {e}")
            raise

    def get_status(self) -> Dict[str, any]:
        """Retorna status da config de IA pro admin dashboard (snapshot estático).
        Pra valores em RUNTIME, use `get_runtime_status()` async.
        """
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "configured": self.client is not None,
            "api_key_set": bool(settings.AI_API_KEY),
            "api_key_preview": (
                settings.AI_API_KEY[:8] + "..." + settings.AI_API_KEY[-4:]
                if settings.AI_API_KEY else "(vazio)"
            ),
        }

    async def get_runtime_status(self) -> Dict[str, any]:
        """Retorna status da config de IA usando DB > .env."""
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            cfg = await rc.ai_config(db)
        api_key = cfg["api_key"]
        return {
            "provider": cfg["provider"],
            "model": cfg["model"],
            "base_url": cfg["base_url"],
            "configured": bool(cfg["configured"]),
            "api_key_set": bool(api_key),
            "api_key_preview": (
                api_key[:8] + "..." + api_key[-4:] if api_key else "(vazio)"
            ),
            # Flag pra UI: diz se valor veio do DB (editado) ou do .env
            "source": {
                "AI_API_KEY": "db" if (await self._db_has(db, "AI_API_KEY")) else "env",
                "AI_BASE_URL": "db" if (await self._db_has(db, "AI_BASE_URL")) else "env",
                "AI_MODEL": "db" if (await self._db_has(db, "AI_MODEL")) else "env",
                "AI_PROVIDER": "db" if (await self._db_has(db, "AI_PROVIDER")) else "env",
            },
        }

    async def _db_has(self, db, key: str) -> bool:
        from sqlalchemy import select
        res = await db.execute(
            select(models.SystemConfig.value).where(models.SystemConfig.key == key)
        )
        v = res.scalar_one_or_none()
        return v is not None and v != ""


# Singleton
ai_service = AIService()
