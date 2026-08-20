"""
AYRIA - AI Service com Retry + Circuit Breaker
MiniMax (única IA) com resiliência:
- 3 tentativas com exponential backoff (1s, 2s, 4s)
- Circuit breaker: se falhar 5x em 1min, para de tentar por 5min (protege API)
- Fallback message amigável se tudo falhar
"""
from typing import List, Dict, Optional
from openai import AsyncOpenAI
import asyncio
import time
import logging
from database import settings
from services.ai_usage_monitor import record_call, should_alert

logger = logging.getLogger(__name__)


class AIService:
    """Cliente IA: APENAS MiniMax via AI_BASE_URL."""

    def __init__(self):
        self.model = settings.AI_MODEL
        self.base_url = settings.AI_BASE_URL
        self.provider = "MiniMax"

        if not settings.AI_API_KEY:
            logger.warning("⚠️ AI_API_KEY não configurada. Defina AI_API_KEY no .env")
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=settings.AI_API_KEY,
                base_url=settings.AI_BASE_URL,
            )
            logger.info(f"✅ AI client (MiniMax): {settings.AI_BASE_URL} | model={self.model}")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Envia mensagem pra MiniMax com retry + circuit breaker.

        Returns:
            Conteúdo da resposta da IA, ou mensagem de fallback se tudo falhar.

        Raises:
            RuntimeError: Se IA não configurada ou circuit breaker aberto.
        """
        if not self.client:
            raise RuntimeError(
                "AI não configurada. Defina AI_API_KEY no .env (MiniMax)"
            )

        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        # Circuit breaker: se muitas falhas recentes, abortar rápido
        global _recent_failures, _circuit_open_until
        now = time.time()
        if _circuit_open_until > now:
            wait = int(_circuit_open_until - now)
            raise RuntimeError(
                f"Circuit breaker aberto após falhas recentes. "
                f"Tente novamente em {wait}s."
            )

        # 3 tentativas com exponential backoff
        last_error = None
        for attempt in range(3):
            try:
                resp = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=30,  # 30s por tentativa
                )
                # Sucesso: reset circuit breaker + registra uso
                _recent_failures = 0
                record_call()
                return resp
            except Exception as e:
                last_error = e
                logger.warning(
                    f"🔄 MiniMax tentativa {attempt + 1}/3 falhou: "
                    f"{type(e).__name__}: {str(e)[:200]}"
                )
                if attempt < 2:  # não espera no último
                    await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s

        # 3 tentativas falharam: registra no circuit breaker
        _recent_failures += 1
        if _recent_failures >= 5:
            _circuit_open_until = time.time() + 300  # 5min
            logger.error(
                f"🚨 Circuit breaker ABERTO após {_recent_failures} falhas. "
                f"IA parada por 5min."
            )

        raise RuntimeError(
            f"MiniMax falhou 3x: {type(last_error).__name__}: {str(last_error)[:200]}"
        )

    async def chat_with_fallback(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        fallback_message: str = "Tô com uma instabilidade técnica agora. Pode tentar de novo em uns segundos? 💜",
    ) -> str:
        """
        Igual a chat() mas retorna fallback_message em vez de raise.
        Útil quando o chat não pode falhar (ex: chat público).
        """
        try:
            return await self.chat(messages, system_prompt)
        except Exception as e:
            logger.error(f"Fallback ativado: {e}")
            return fallback_message

    def get_status(self) -> Dict[str, any]:
        """Status pra dashboard admin."""
        now = time.time()
        circuit_open = _circuit_open_until > now
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
            "circuit_breaker": {
                "open": circuit_open,
                "failures_last_minute": _recent_failures,
                "reopens_in_seconds": int(_circuit_open_until - now) if circuit_open else 0,
            },
        }


# Circuit breaker state (in-memory, single-process)
_recent_failures = 0
_circuit_open_until = 0


# Singleton
ai_service = AIService()
