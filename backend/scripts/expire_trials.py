#!/usr/bin/env python3
"""
AYRIA — Cron: expira trials vencidos (20/08/2026)

Executa diariamente às 03:00 (configurado em /etc/cron.d/ayria-expire-trials).
Para staging: roda direto no venv.
Para prod: mesmo path, service account ayria-app.

USO:
    /opt/ayria/.venv/bin/python3 /opt/ayria/backend/scripts/expire_trials.py

EXIT:
    0 = sucesso (mesmo se 0 trials expiraram)
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Adiciona o backend no PYTHONPATH
BACKEND_DIR = Path("/opt/ayria/backend")
sys.path.insert(0, str(BACKEND_DIR))

# Carrega .env-staging ou .env conforme o environment
env_file = Path("/etc/ayria/.env-staging")
if not env_file.exists():
    env_file = Path("/etc/ayria/.env")
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k not in os.environ:  # não sobrescreve se já tem
            os.environ[k] = v

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("expire_trials")


async def main():
    from database import AsyncSessionLocal
    from services.credit_service import expire_overdue_trials

    async with AsyncSessionLocal() as db:
        try:
            expired = await expire_overdue_trials(db)
            logger.info(f"Cron expire_trials concluido: {expired} trials expirados")
        except Exception as e:
            logger.exception(f"Erro no cron expire_trials: {e}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
