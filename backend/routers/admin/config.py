"""
admin/config.py — Configurações do sistema + debug Qdrant

Endpoints:
  GET /config/ai       → config IA em uso
  GET /config/system   → status geral
  GET /debug/qdrant    → diagnóstico Qdrant (reachability, latência, coleções)
"""
from ._base import (
    APIRouter, Depends,
    select,
    uuid, logging, json,
    get_db, require_admin,
    storage_service, models,
)
import urllib.request, urllib.error, time as _time, socket

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])


@router.get("/config/ai", response_model=dict)
async def get_ai_config(admin=Depends(require_admin)):
    """Retorna config da IA em uso (provider, modelo, URL, status da chave)."""
    from database import settings
    from services.ai_service import ai_service
    return {
        "ai": ai_service.get_status(),
        "embedding_provider": "MiniMax (ou hash fallback se MiniMax não suportar embeddings)",
        "azure_storage": {
            "configured": bool(storage_service.sas_url),
            "container": storage_service.container_name,
            "sas_expires": "2036-06-28 (10 anos)",
            "use_local_fallback": storage_service.use_local,
        },
        "environment": settings.ENVIRONMENT,
        "rules": [
            "APENAS MiniMax (regra absoluta do sistema)",
            "OpenAI foi REMOVIDO COMPLETAMENTE",
            "Modelo padrão: MiniMax-M3",
        ],
    }


@router.get("/config/system", response_model=dict)
async def get_system_config(admin=Depends(require_admin)):
    """Retorna status geral do sistema."""
    from database import settings
    from services.ai_service import ai_service
    return {
        "environment": settings.ENVIRONMENT,
        "ai": ai_service.get_status(),
        "azure": {
            "configured": bool(storage_service.sas_url),
            "container": storage_service.container_name,
            "use_local_fallback": storage_service.use_local,
        },
        "cors_origins": settings.CORS_ORIGINS.split(","),
        "jwt_expire_minutes": settings.JWT_EXPIRE_MINUTES,
    }


@router.get("/debug/qdrant", response_model=dict)
async def debug_qdrant(admin=Depends(require_admin)):
    """Diagnóstico do Qdrant: retorna URL efetiva, status, coleções, latência."""
    from database import settings

    url = settings.QDRANT_URL
    api_key_set = bool(settings.QDRANT_API_KEY)

    out = {
        "qdrant_url": url,
        "qdrant_api_key_set": api_key_set,
        "qdrant_api_key_preview": (settings.QDRANT_API_KEY[:8] + "...") if api_key_set else None,
        "reachable": False,
        "latency_ms": None,
        "collections": [],
        "error": None,
    }

    try:
        start = _time.time()
        health_url = url.rstrip("/") + "/healthz"
        req = urllib.request.Request(health_url, method="GET")
        if api_key_set:
            req.add_header("api-key", settings.QDRANT_API_KEY)
        with urllib.request.urlopen(req, timeout=3) as resp:
            out["latency_ms"] = int((_time.time() - start) * 1000)
            out["healthz_body"] = resp.read()[:200].decode("utf-8", errors="replace")
        collections_url = url.rstrip("/") + "/collections"
        req2 = urllib.request.Request(collections_url, method="GET")
        if api_key_set:
            req2.add_header("api-key", settings.QDRANT_API_KEY)
        with urllib.request.urlopen(req2, timeout=3) as resp2:
            data = json.loads(resp2.read())
            out["collections"] = [c["name"] for c in data.get("result", {}).get("collections", [])]
        out["reachable"] = True
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        try:
            host = url.split("://", 1)[-1].split(":", 1)[0]
            socket.gethostbyname(host)
        except Exception as dns_err:
            out["dns_error"] = f"{type(dns_err).__name__}: {str(dns_err)[:200]}"

    return out
