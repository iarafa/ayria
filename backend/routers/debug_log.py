"""
AYRIA - Debug Log Endpoint
Sistema de log interno que captura TUDO do backend sem depender do Coolify.
Permite ao admin ler logs de TODAS as rotas (request middleware) + erros.

Arquivo de log principal: /app/logs/ayria.log (configurável via AYRIA_LOG_DIR)
"""
import os
import glob
import re
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import PlainTextResponse

from utils.security import require_admin

router = APIRouter()
logger = logging.getLogger(__name__)

# Caminhos padrão de log (configurável via env)
LOG_DIR = os.getenv("AYRIA_LOG_DIR", "/app/logs")
LOG_FILE = os.path.join(LOG_DIR, "ayria.log")

# Regex pra detectar erros / exceções
ERROR_PATTERNS = [
    r"\bERROR\b",
    r"\bEXCEPTION\b",
    r"\bTraceback",
    r"\bUNCAUGHT\b",
    r"❌",
    r"\bFailed\b",
    r"status: \d{3}.*[45]\d{2}",
]


def _list_log_files() -> list:
    """Lista todos os arquivos de log (atual + backups rotacionados)."""
    if not os.path.exists(LOG_DIR):
        return []
    files = glob.glob(os.path.join(LOG_DIR, "ayria.log*"))
    return sorted(files, key=lambda p: os.path.getmtime(p), reverse=True)


@router.get("/debug/log", response_class=PlainTextResponse)
async def get_debug_log(
    lines: int = Query(default=300, le=3000, description="Número de linhas (do final)"),
    filter: str = Query(default="", description="Filtro substring (case-insensitive)"),
    level: str = Query(default="", description="Filtro por nível (INFO/WARNING/ERROR/EXCEPTION)"),
    admin=Depends(require_admin),
):
    """
    Retorna últimas N linhas do log do AYRIA (mais recente no fim).
    Filtros opcionais: substring + nível mínimo.
    """
    files = _list_log_files()
    if not files:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum log encontrado em {LOG_DIR}. O backend ainda não gravou nada.",
        )

    main_log = files[0]  # mais recente

    try:
        with open(main_log, "r", encoding="utf-8", errors="replace") as f:
            content = f.readlines()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler {main_log}: {e}")

    tail = content[-lines:]

    # Aplica filtros
    if filter:
        ft = filter.lower()
        tail = [ln for ln in tail if ft in ln.lower()]
    if level:
        lvl = level.upper()
        tail = [ln for ln in tail if f"| {lvl}" in ln.upper()]

    header = (
        f"=== AYRIA Internal Log ===\n"
        f"Arquivo: {main_log}\n"
        f"Tamanho: {os.path.getsize(main_log):,} bytes\n"
        f"Linhas retornadas: {len(tail)}/{lines}\n"
        f"Filtro substring: '{filter}'\n"
        f"Filtro nível: '{level}'\n"
        f"Total arquivos disponíveis: {len(files)}\n"
        f"Gerado em: {datetime.now(timezone.utc).isoformat()}\n"
        f"{'='*60}\n\n"
    )
    return header + "".join(tail)


@router.get("/debug/errors", response_class=PlainTextResponse)
async def get_recent_errors(
    lines: int = Query(default=100, le=1000),
    admin=Depends(require_admin),
):
    """Retorna apenas linhas com ERROR, EXCEPTION, Traceback, UNCAUGHT."""
    files = _list_log_files()
    if not files:
        raise HTTPException(status_code=404, detail=f"Nenhum log em {LOG_DIR}")

    main_log = files[0]
    try:
        with open(main_log, "r", encoding="utf-8", errors="replace") as f:
            content = f.readlines()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    pattern = re.compile("|".join(ERROR_PATTERNS), re.IGNORECASE)
    errors = [ln for ln in content if pattern.search(ln)]
    tail = errors[-lines:]

    header = (
        f"=== AYRIA ERROS RECENTES ===\n"
        f"Arquivo: {main_log}\n"
        f"Erros retornados: {len(tail)}/{len(errors)} (total: {len(errors)})\n"
        f"Gerado em: {datetime.now(timezone.utc).isoformat()}\n"
        f"{'='*60}\n\n"
    )
    return header + "".join(tail)


@router.get("/debug/log/info")
async def get_log_info(admin=Depends(require_admin)) -> dict:
    """Info sobre logs disponíveis."""
    files = _list_log_files()
    info = {
        "log_dir": LOG_DIR,
        "log_file": LOG_FILE,
        "files": [],
        "errors_count_last_1000": 0,
    }
    for f in files:
        stat = os.stat(f)
        info["files"].append({
            "path": f,
            "size_bytes": stat.st_size,
            "size_human": f"{stat.st_size/1024:.1f}KB",
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        })

    # Conta erros nas últimas 1000 linhas do principal
    if files:
        try:
            with open(files[0], "r", encoding="utf-8", errors="replace") as fh:
                tail = fh.readlines()[-1000:]
            pattern = re.compile("|".join(ERROR_PATTERNS), re.IGNORECASE)
            info["errors_count_last_1000"] = sum(1 for ln in tail if pattern.search(ln))
        except Exception as e:
            info["count_error"] = str(e)

    return info