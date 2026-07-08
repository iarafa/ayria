"""
AYRIA - Debug Log Endpoint
Permite ao admin ler logs do backend direto do frontend.
Útil pra debug quando o reindex trava e o admin não consegue ver logs do Coolify.
"""
import os
import logging
import glob
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import PlainTextResponse

from utils.security import require_admin  # ajuste pro seu sistema de auth se necessário

router = APIRouter()
logger = logging.getLogger(__name__)

# Caminhos comuns de log do uvicorn + container
LOG_PATHS = [
    "/var/log/uvicorn.log",
    "/app/ayria-rag.log",
    "/tmp/ayria-rag.log",
    "/app/logs/ayria.log",
]


@router.get("/debug/log", response_class=PlainTextResponse)
async def get_debug_log(
    lines: int = Query(default=200, le=2000),
    filter: str = Query(default="", description="Filtro de substring (case-insensitive)"),
    admin=Depends(require_admin),
):
    """
    Retorna últimas N linhas do log do backend (mais recente no fim).
    Filtra por substring se `filter` for fornecido.
    """
    candidates = []

    # 1) Arquivo padrão do uvicorn (se acessível)
    for path in LOG_PATHS:
        if os.path.exists(path) and os.access(path, os.R_OK):
            candidates.append(path)

    # 2) Descobre logs em /var/log
    candidates.extend(sorted(glob.glob("/var/log/*.log")))

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail="Nenhum arquivo de log acessível. Tentou: " + ", ".join(LOG_PATHS),
        )

    # Pega o maior / mais recente
    main_log = max(candidates, key=lambda p: os.path.getmtime(p))

    try:
        with open(main_log, "r", encoding="utf-8", errors="replace") as f:
            content = f.readlines()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler {main_log}: {e}")

    # Pega as últimas N linhas
    tail = content[-lines:]

    # Filtra se preciso
    if filter:
        ft = filter.lower()
        tail = [ln for ln in tail if ft in ln.lower()]

    header = (
        f"=== AYRIA Debug Log ===\n"
        f"Arquivo: {main_log}\n"
        f"Tamanho: {os.path.getsize(main_log)} bytes\n"
        f"Linhas retornadas: {len(tail)}/{lines}\n"
        f"Filtrado por: '{filter}'\n"
        f"Gerado em: {datetime.now(timezone.utc).isoformat()}\n"
        f"{'='*60}\n\n"
    )

    return header + "".join(tail)


@router.get("/debug/log/info", response_model=dict)
async def get_log_info(admin=Depends(require_admin)):
    """Info sobre arquivos de log disponíveis (sem ler conteúdo)."""
    info = {"available_files": [], "missing": []}

    for path in LOG_PATHS:
        if os.path.exists(path):
            stat = os.stat(path)
            info["available_files"].append({
                "path": path,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "readable": os.access(path, os.R_OK),
            })
        else:
            info["missing"].append(path)

    # Glob
    extras = sorted(glob.glob("/var/log/*.log"))
    info["extra_logs"] = []
    for path in extras:
        if path not in [f["path"] for f in info["available_files"]]:
            stat = os.stat(path)
            info["extra_logs"].append({
                "path": path,
                "size_bytes": stat.st_size,
            })

    return info