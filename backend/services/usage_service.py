"""
AYRIA — Usage Service (21/07/2026)
Rastreia cada chamada de IA: tokens input/output, custo USD, latency.
Usado pelo dashboard admin pra billing reconciliation.
"""

import logging
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import models

logger = logging.getLogger(__name__)

# MiniMax pay-as-you-go rates (Standard, permanent 50% off)
# Atualizado 21/07/2026 via https://platform.minimax.io/docs/guides/pricing-paygo
MODEL_RATES = {
    "MiniMax-M3":      {"input": Decimal("0.30"), "output": Decimal("1.20")},  # ≤512K input
    "MiniMax-M2.7":    {"input": Decimal("0.30"), "output": Decimal("1.20")},
    "MiniMax-M2.7-highspeed": {"input": Decimal("0.60"), "output": Decimal("2.40")},
}


def calculate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> dict:
    """
    Calcula custo em USD baseado nos rates do model.
    Retorna dict com input_cost, output_cost, total_cost (Decimal).
    Se model não tá no MAP, retorna zero (mas loga warning).
    """
    rates = MODEL_RATES.get(model)
    if not rates:
        logger.warning(f"⚠️ Model '{model}' sem rate conhecido — custo zerado")
        return {"input": Decimal("0"), "output": Decimal("0"), "total": Decimal("0")}

    input_cost = (Decimal(prompt_tokens) / Decimal(1_000_000)) * rates["input"]
    output_cost = (Decimal(completion_tokens) / Decimal(1_000_000)) * rates["output"]
    total = input_cost + output_cost

    return {
        "input": input_cost.quantize(Decimal("0.000001")),
        "output": output_cost.quantize(Decimal("0.000001")),
        "total": total.quantize(Decimal("0.000001")),
    }


async def log_ai_usage(
    db: AsyncSession,
    user_id: Optional[str],
    action_type_id: Optional[str],
    chat_id: Optional[str],
    message_id: Optional[str],
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    response_ms: Optional[int] = None,
    status: str = "success",
    error_message: Optional[str] = None,
) -> Optional[models.AIUsageLog]:
    """
    Grava log de uso de IA. Idempotente (não falha se der erro).
    Retorna o registro criado ou None em caso de falha.
    """
    try:
        costs = calculate_cost_usd(model, prompt_tokens, completion_tokens)
        total_tokens = prompt_tokens + completion_tokens

        log_entry = models.AIUsageLog(
            user_id=user_id,
            action_type_id=action_type_id,
            chat_id=chat_id,
            message_id=message_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_input_usd=costs["input"],
            cost_output_usd=costs["output"],
            cost_total_usd=costs["total"],
            response_ms=response_ms,
            status=status,
            error_message=error_message,
        )
        db.add(log_entry)
        await db.flush()  # não commita — caller controla transação
        logger.debug(
            f"📊 AI usage logged: model={model} tokens={total_tokens} "
            f"cost_usd={costs['total']} user={user_id}"
        )
        return log_entry
    except Exception as e:
        logger.error(f"❌ Falha ao gravar ai_usage_log: {e}")
        return None