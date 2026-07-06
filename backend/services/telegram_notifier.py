"""
Telegram Notifier — envia mensagens pro admin via Telegram.

Usado pelo chat endpoint pra avisar em TEMPO REAL quando o supervisor
detecta risco. Não bloqueia o chat: best-effort, sem retry forte.

Env vars (opcional):
    TELEGRAM_BOT_TOKEN  — token do bot (default em código)
    TELEGRAM_CHAT_ID    — chat_id do admin (default 779495783)

Se não estiver configurado, todas as funções viram no-op silenciosas.
"""
import os
import logging
from datetime import datetime, timezone, timedelta
import re

import httpx

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8622724474:AAHlnGciMwJYgPCUcl_YBZrxvKv6jFgpzVE")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "779495783")

BR_TZ = timezone(timedelta(hours=-3))

LEVEL_EMOJI = {
    "URGENCIA": "🚨",
    "ATENCAO": "⚠️",
    "NORMAL": "✅",
}


def _build_alert_message(
    *,
    user_email: str,
    level: str,
    signals: list[str],
    content_excerpt: str,
    ia_confirmed: bool | None,
    alert_id: int | None,
) -> str:
    """Monta msg simples SEM markdown (raw)."""
    emoji = LEVEL_EMOJI.get(level, "ℹ️")
    confirm_state = (
        "✅ IA confirmou"
        if ia_confirmed is True
        else "⏳ Aguardando IA (pré-check regex)"
        if ia_confirmed is False
        else "⚙️ Legado (sem status IA)"
    )
    sigs = ", ".join(signals[:4]) if signals else "(sem sinal específico)"
    timestamp = datetime.now(BR_TZ).strftime("%d/%m/%Y %H:%M:%S")
    return (
        f"{emoji} ALERTA SUPERVISOR AYRIA — nível {level}\n"
        f"\n"
        f"👤 Usuário: {user_email}\n"
        f"🕐 Quando: {timestamp} BR\n"
        f"🎯 Sinais: {sigs}\n"
        f"🤖 Status IA: {confirm_state}\n"
        f"\n"
        f"💬 Mensagem:\n"
        f"\"{content_excerpt}\"\n"
        f"\n"
        f"🆔 Alerta #{alert_id} — acesse o painel de Supervisão pra revisar."
    )


async def send_supervisor_alert(
    *,
    user_email: str,
    level: str,
    signals: list[str],
    content_excerpt: str,
    ia_confirmed: bool | None,
    alert_id: int | None,
) -> None:
    """Envia notificação ao admin. Best-effort: erro não derruba o chat."""
    if not BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN não configurado — pulando notificação")
        return
    logger.warning(f"📤 Telegram send iniciado: user={user_email} level={level} alert_id={alert_id}")
    try:
        msg = _build_alert_message(
            user_email=user_email,
            level=level,
            signals=signals,
            content_excerpt=content_excerpt,
            ia_confirmed=ia_confirmed,
            alert_id=alert_id,
        )
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        # SEM parse_mode — texto puro (mais tolerante, sem escape issues)
        payload = {
            "chat_id": ADMIN_CHAT_ID,
            "text": msg,
            "disable_web_page_preview": True,
        }
        logger.warning(f"📤 Telegram URL montada, vai chamar httpx...")
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, json=payload)
            logger.warning(f"📤 Telegram response status={r.status_code}")
            if r.status_code != 200:
                logger.warning(
                    f"Telegram não aceitou: {r.status_code} {r.text[:200]}"
                )
            else:
                logger.warning(
                    f"📨 Telegram notificação enviada (alerta #{alert_id}, {level})"
                )
    except Exception as e:
        logger.error(f"Erro ao enviar notificação Telegram (alerta #{alert_id}): {e}", exc_info=True)
