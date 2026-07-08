"""
AYRIA - URL Detector
Detecta automaticamente a URL pública base (front) do app.
Usado pra construir links de email (verificação, reset senha, etc).

Prioridade:
  1. PUBLIC_BASE_URL  (env var explícita — vence tudo)
  2. COOLIFY_FQDN     (Coolify seta automaticamente)
  3. COOLIFY_URL      (Coolify alternativo)
  4. Hostname hint    (detecta "coolify" no nome do container)
  5. LOCAL_BASE_URL   (env var explícita pro dev)
  6. Fallback hardcoded
"""
import os
import socket
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Defaults hardcoded
DEFAULT_PROD_URL = "https://ayria.tecia.app"
DEFAULT_LOCAL_URL = "http://192.168.3.37:8093"


def get_public_base_url() -> str:
    """
    Retorna a URL pública base do front (sem barra final).
    """
    # 1. Override explícito
    if url := os.getenv("PUBLIC_BASE_URL"):
        url = url.rstrip("/")
        logger.debug(f"URL via PUBLIC_BASE_URL: {url}")
        return url

    # 2. Coolify FQDN (prioridade alta em produção)
    if fqdn := os.getenv("COOLIFY_FQDN"):
        url = f"https://{fqdn}".rstrip("/")
        logger.debug(f"URL via COOLIFY_FQDN: {url}")
        return url

    # 3. Coolify URL genérica
    if url := os.getenv("COOLIFY_URL"):
        url = url.rstrip("/")
        logger.debug(f"URL via COOLIFY_URL: {url}")
        return url

    # 4. Hostname hint
    hostname = (os.getenv("HOSTNAME") or socket.gethostname() or "").lower()
    if "coolify" in hostname or os.getenv("COOLIFY_APP_NAME"):
        logger.debug(f"URL via hostname coolify: {DEFAULT_PROD_URL}")
        return DEFAULT_PROD_URL

    # 5. Local override
    if url := os.getenv("LOCAL_BASE_URL"):
        url = url.rstrip("/")
        logger.debug(f"URL via LOCAL_BASE_URL: {url}")
        return url

    # 6. Fallback
    logger.debug(f"URL fallback: {DEFAULT_LOCAL_URL}")
    return DEFAULT_LOCAL_URL


def build_verification_url(token: str) -> str:
    """Monta URL completa de verificação de email."""
    base = get_public_base_url()
    return f"{base}/verify-email?token={token}"
