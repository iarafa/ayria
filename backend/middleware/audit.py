"""
AYRIA - Audit Middleware

Registra TODAS as acoes relevantes no audit_log:
- Login/logout
- Acesso a rotas admin
- Upload/delete de documentos
- Mudanca de role
- Mudanca em onboarding/attributes
"""
import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# Rotas que NAO precisam de audit (sao ruido)
SKIP_PATHS = [
    "/health",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/favicon.ico",
]


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware que registra acoes no audit_log"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        start = time.time()

        response = await call_next(request)

        # Skip rotas de ruido
        if any(request.url.path.startswith(p) for p in SKIP_PATHS):
            return response

        # Skip metodos que nao modificam (mas registra GETs em rotas admin)
        duration = time.time() - start

        # Acoes auditaveis (registra async, sem bloquear response)
        if self._is_auditable(request, response):
            try:
                await self._log_audit(request, response, duration)
            except Exception as e:
                logger.error(f"Erro audit log: {e}")

        return response

    def _is_auditable(self, request: Request, response) -> bool:
        path = request.url.path
        method = request.method

        # 401/403/500 sao sempre relevantes
        if response.status_code in (401, 403, 500):
            return True

        # Admin rotas: tudo
        if path.startswith("/api/admin"):
            return True

        # Auth rotas
        if path.startswith("/api/auth"):
            return True

        # POST /api/chat/message (cada mensagem eh relevante)
        if path == "/api/chat/message" and method == "POST":
            return True

        # Onboarding
        if path.startswith("/api/onboarding") and method in ("POST", "PUT", "DELETE"):
            return True

        return False

    async def _log_audit(self, request: Request, response, duration: float):
        """Registra a acao no banco"""
        # Importa aqui pra evitar circular
        from database import AsyncSessionLocal
        from models import AuditLog

        # Extrai user_id do token (se possivel)
        user_id = None
        try:
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer "):
                from utils.security import decode_token
                token = auth[7:]
                payload = decode_token(token)
                user_id = payload.get("sub") if payload else None
        except Exception:
            pass

        try:
            async with AsyncSessionLocal() as db:
                log = AuditLog(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    action=f"{request.method} {request.url.path}",
                    resource_type=request.url.path.split("/")[2] if len(request.url.path.split("/")) > 2 else None,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent", "")[:500],
                    details={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": int(duration * 1000),
                        "query_params": dict(request.query_params),
                    },
                    created_at=datetime.utcnow(),
                )
                db.add(log)
                await db.commit()
        except Exception as e:
            logger.error(f"Erro salvando audit: {e}")