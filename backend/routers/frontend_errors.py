"""
AYRIA - Frontend Errors Endpoint (21/07/2026 00:35)

Recebe logs de erro vindos do navegador ANTES que cheguem no backend.
Quando o browser dá JS error / promise rejeitada / axios falhou → frontend envia aqui.
Salva em arquivo separado + alerta Telegram se volume crítico.

Tipologia:
- js_error: window.onerror / unhandledrejection
- axios_error: request nunca chegou OU veio 4xx/5xx
- react_error: ErrorBoundary pega
- manual: front jogou explicitamente
"""
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db

router = APIRouter()
logger = logging.getLogger("frontend.errors")

LOG_FILE = Path("/home/peron/projects/ayria/logs/frontend-errors.log")


class FrontendErrorReport(BaseModel):
    type: str  # js_error | axios_error | react_error | manual
    message: str
    stack: Optional[str] = None
    url: Optional[str] = None  # window.location.href
    user_agent: Optional[str] = None
    extra: Optional[dict] = None
    timestamp: Optional[str] = None


class BatchReport(BaseModel):
    errors: List[FrontendErrorReport]


def _append_log(report: FrontendErrorReport):
    """Append 1 linha JSON no arquivo de log"""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": report.timestamp or datetime.utcnow().isoformat(),
            "type": report.type,
            "message": report.message[:500] if report.message else "",
            "stack": (report.stack or "")[:2000],
            "url": report.url,
            "ua": report.user_agent,
            "extra": report.extra,
        }
        with LOG_FILE.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.exception(f"Falha escrevendo frontend-errors.log: {e}")


@router.post("/api/errors/frontend")
async def receive_error(report: FrontendErrorReport, db: AsyncSession = Depends(get_db)):
    """
    Recebe 1 erro do frontend e grava no log.
    Não precisa auth — é pra ser chamado por qualquer user (ou anônimo).
    """
    _append_log(report)
    logger.warning(
        f"FRONTEND ERROR [{report.type}] {report.url or 'no-url'}: {report.message[:200]}"
    )
    return {"ok": True, "logged_at": datetime.utcnow().isoformat()}


@router.post("/api/errors/frontend/batch")
async def receive_batch(batch: BatchReport, db: AsyncSession = Depends(get_db)):
    """Recebe lote (browser pode estar offline e mandar tudo de uma vez quando volta)."""
    for r in batch.errors:
        _append_log(r)
    logger.warning(f"FRONTEND BATCH: {len(batch.errors)} errors")
    return {"ok": True, "count": len(batch.errors)}


@router.get("/api/admin/frontend-errors")
async def list_recent(limit: int = 50, db: AsyncSession = Depends(get_db), admin=Depends(__import__("utils.security", fromlist=["require_admin"]).require_admin)):
    """Admin vê os últimos erros do frontend (tail do arquivo)."""
    if not LOG_FILE.exists():
        return {"items": [], "count": 0, "file": str(LOG_FILE)}
    lines = LOG_FILE.read_text().splitlines()[-limit:]
    items = [json.loads(l) for l in lines if l.strip()]
    return {"items": items, "count": len(items), "file": str(LOG_FILE)}
