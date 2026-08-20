"""
AYRIA - AI Usage Monitor

Conta chamadas ao MiniMax e alerta no Telegram se ultrapassar limite.
Em produção, é executado a cada hora via cron.

Limites configuráveis:
- 1000 chamadas/hora: WARN
- 5000 chamadas/hora: ALERT (provável abuso)
"""
import os
import json
import time
import logging
from pathlib import Path
from collections import deque
from threading import Lock

logger = logging.getLogger(__name__)

# Limites
WARN_THRESHOLD = 1000    # chamadas/hora
ALERT_THRESHOLD = 5000   # chamadas/hora (provável bug ou abuso)
CHECK_INTERVAL = 3600    # 1 hora

# Estado em memória + persistência em arquivo
STATE_FILE = Path("/var/log/ayria/ai_usage.json")
_state_lock = Lock()
_call_timestamps: deque[float] = deque()  # timestamps das últimas 1h


def record_call() -> None:
    """Registra uma chamada ao MiniMax."""
    now = time.time()
    with _state_lock:
        _call_timestamps.append(now)
        # Limpa timestamps > 1h atrás
        cutoff = now - 3600
        while _call_timestamps and _call_timestamps[0] < cutoff:
            _call_timestamps.popleft()


def calls_last_hour() -> int:
    """Número de chamadas na última hora."""
    now = time.time()
    with _state_lock:
        cutoff = now - 3600
        while _call_timestamps and _call_timestamps[0] < cutoff:
            _call_timestamps.popleft()
        return len(_call_timestamps)


def should_warn() -> bool:
    """Deve avisar (WARN level: >1000/hora)?"""
    return calls_last_hour() >= WARN_THRESHOLD


def should_alert() -> bool:
    """Deve alertar (ALERT level: >5000/hora)?"""
    return calls_last_hour() >= ALERT_THRESHOLD


async def send_usage_alert_if_needed() -> None:
    """
    Verifica uso e envia Telegram se passou dos limites.
    Chamado periodicamente (a cada hora via cron).
    """
    count = calls_last_hour()

    if not should_alert() and not should_warn():
        logger.info(f"AI usage OK: {count} chamadas/hora")
        return

    # Carrega env vars do Telegram
    if not os.path.exists("/etc/ayria/.env"):
        logger.warning("/etc/ayria/.env não existe")
        return

    with open("/etc/ayria/.env") as f:
        env_lines = f.readlines()

    env = {}
    for line in env_lines:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.strip().split("=", 1)
            env[k] = v.strip().strip('"').strip("'")

    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "779495783")

    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN não configurado")
        return

    if should_alert():
        emoji = "🚨"
        tag = "AI-COST-ALERT"
        msg = f"<b>USO DE IA ACIMA DO LIMITE!</b>\n\nChamadas na última hora: <b>{count}</b>\nLimite: {ALERT_THRESHOLD}\n\n⚠️ Provável abuso ou bug. Investigar imediatamente."
    else:  # warn
        emoji = "⚠️"
        tag = "AI-COST-WARN"
        msg = f"<b>Uso de IA elevado</b>\n\nChamadas na última hora: <b>{count}</b>\nLimite warn: {WARN_THRESHOLD}\n\nMonitorar tendência."

    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": f"{emoji} {tag} AYRIA\n\n{msg}",
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
        if r.status_code == 200:
            logger.info(f"Telegram alerta enviado: {tag}")
        else:
            logger.warning(f"Falha Telegram: {r.status_code}")


def get_stats() -> dict:
    """Stats pra dashboard."""
    return {
        "calls_last_hour": calls_last_hour(),
        "warn_threshold": WARN_THRESHOLD,
        "alert_threshold": ALERT_THRESHOLD,
    }
