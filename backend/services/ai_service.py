"""
AYRIA - AI Service
Integração com Minimax (default) ou OpenAI (fallback).
OpenAI-compatible API.
"""
from typing import List, Dict, Optional, AsyncIterator
from openai import AsyncOpenAI
import logging

from database import settings

logger = logging.getLogger(__name__)


class AIService:
    """Cliente IA com fallback Minimax → OpenAI"""
    
    def __init__(self):
        self.minimax_client = None
        self.openai_client = None
        
        if settings.MINIMAX_API_KEY:
            self.minimax_client = AsyncOpenAI(
                api_key=settings.MINIMAX_API_KEY,
                base_url=settings.MINIMAX_BASE_URL,
            )
            logger.info(f"Minimax client configured (model={settings.MINIMAX_MODEL})")
        
        if settings.OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url="https://api.openai.com/v1",
            )
            logger.info(f"OpenAI fallback configured (model={settings.OPENAI_MODEL})")
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
    ):
        """
        Envia mensagem pra IA.
        Tenta Minimax primeiro, fallback OpenAI.
        """
        # Insere system prompt se fornecido
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
        
        # Tenta Minimax primeiro
        if self.minimax_client:
            try:
                if stream:
                    return self.minimax_client.chat.completions.create(
                        model=settings.MINIMAX_MODEL,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=True,
                    )
                else:
                    return await self.minimax_client.chat.completions.create(
                        model=settings.MINIMAX_MODEL,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
            except Exception as e:
                logger.warning(f"Minimax falhou, tentando OpenAI: {e}")
        
        # Fallback OpenAI
        if self.openai_client:
            try:
                if stream:
                    return self.openai_client.chat.completions.create(
                        model=settings.OPENAI_MODEL,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=True,
                    )
                else:
                    return await self.openai_client.chat.completions.create(
                        model=settings.OPENAI_MODEL,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
            except Exception as e:
                logger.error(f"OpenAI também falhou: {e}")
                raise
        
        raise RuntimeError("Nenhum cliente IA configurado (MINIMAX_API_KEY ou OPENAI_API_KEY)")


# Singleton
ai_service = AIService()
