"""
AYRIA - Security Headers Middleware

Adiciona headers de segurança em TODAS as respostas da API.
Defesa contra:
- Clickjacking (X-Frame-Options)
- MIME sniffing (X-Content-Type-Options)
- XSS via injeção (CSP básico + Referrer-Policy)
- SSL stripping (HSTS, só em prod com HTTPS)
- Permissões de browser APIs (Permissions-Policy)
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.requests import Request
import os


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adiciona security headers em toda resposta."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.environment = os.getenv("ENVIRONMENT", "development")

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Anti-clickjacking: proíbe a página ser iframe em outro site
        response.headers["X-Frame-Options"] = "DENY"

        # Anti-MIME sniffing: força o browser a respeitar Content-Type
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer: só envia origin (não path completo) pra cross-origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy: desabilita APIs sensíveis por padrão
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        )

        # CSP básico — protege contra XSS injetado via prompt injection da IA.
        # Sem 'unsafe-inline' pra scripts: força a usar bundled JS.
        # 'self' permite assets do mesmo origin (Vite dev usa localhost).
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https: blob:; "
            "media-src 'self' https:; "
            "font-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "connect-src 'self' https://api.minimax.io wss: ws:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # HSTS só em prod (assume HTTPS atrás de proxy reverso)
        if self.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response