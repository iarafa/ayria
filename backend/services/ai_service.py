"""
AYRIA - AI Service
APENAS MiniMax (regra absoluta do sistema). OpenAI foi REMOVIDO COMPLETAMENTE.
"""
from typing import List, Dict, Optional
from openai import AsyncOpenAI
import logging

from database import settings

logger = logging.getLogger(__name__)


class AIService:
    """Cliente IA: APENAS MiniMax via AI_BASE_URL."""

    def __init__(self):
        self.model = settings.AI_MODEL
        self.base_url = settings.AI_BASE_URL
        self.provider = "MiniMax"

        if not settings.AI_API_KEY:
            logger.warning(
                "⚠️ AI_API_KEY não configurada. Defina AI_API_KEY no .env"
            )
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=settings.AI_API_KEY,
                base_url=settings.AI_BASE_URL,
            )
            logger.info(
                f"✅ AI client (MiniMax): {settings.AI_BASE_URL} | model={self.model}"
            )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        """Envia mensagem pra MiniMax."""
        if not self.client:
            raise RuntimeError(
                "AI não configurada. Defina AI_API_KEY no .env (MiniMax)"
            )

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
        """Retorna status da config de IA pro admin dashboard."""
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


# Singleton
ai_service = AIService()
