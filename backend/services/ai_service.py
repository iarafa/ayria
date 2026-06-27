"""
AYRIA - AI Service
Integração com IA via API OpenAI-compatible.
Configurável pra usar MiniMax, OpenAI ou qualquer provider compatível.
"""
from typing import List, Dict, Optional
from openai import AsyncOpenAI
import logging

from database import settings

logger = logging.getLogger(__name__)


class AIService:
    """Cliente IA com provider configurável via env"""

    def __init__(self):
        self.primary_client = None
        self.fallback_client = None
        self.primary_model = settings.AI_MODEL
        self.fallback_model = settings.OPENAI_MODEL

        # Cliente principal (AI_API_KEY + AI_BASE_URL)
        if settings.AI_API_KEY:
            self.primary_client = AsyncOpenAI(
                api_key=settings.AI_API_KEY,
                base_url=settings.AI_BASE_URL,
            )
            logger.info(f"AI client (primary): {settings.AI_BASE_URL} | model={self.primary_model}")

        # Fallback OpenAI oficial
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != settings.AI_API_KEY:
            self.fallback_client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url="https://api.openai.com/v1",
            )
            logger.info(f"AI client (fallback): OpenAI | model={self.fallback_model}")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        """Envia mensagem pra IA. Tenta primary, fallback OpenAI."""
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        # Tenta primary primeiro
        if self.primary_client:
            try:
                resp = await self.primary_client.chat.completions.create(
                    model=self.primary_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp
            except Exception as e:
                logger.warning(f"Primary AI failed ({settings.AI_BASE_URL}): {e}")

        # Fallback OpenAI
        if self.fallback_client:
            try:
                resp = await self.fallback_client.chat.completions.create(
                    model=self.fallback_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp
            except Exception as e:
                logger.error(f"Fallback AI failed too: {e}")
                raise

        raise RuntimeError(
            "Nenhum cliente IA configurado. Defina AI_API_KEY ou OPENAI_API_KEY no .env"
        )


# Singleton
ai_service = AIService()
