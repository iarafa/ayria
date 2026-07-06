"""
Middleware: garante que NENHUMA resposta da API vai pro cache do navegador.
Crítico pra evitar vazamento entre users no mesmo navegador (computador compartilhado).
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class NoCacheAPIMiddleware(BaseHTTPMiddleware):
    """
    Adiciona headers no-cache em TODAS as respostas /api/*.

    Por quê:
    - Navegador não deve cachear respostas com dados do user
    - Computador compartilhado: user B não pode ver resposta do user A
    - Botão "voltar" do navegador não deve mostrar msgs antigas
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Aplica só nas rotas /api/* (não afeta static files do Vite)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            # Extra segurança: proíbe cache em proxys compartilhados
            response.headers["Vary"] = "Authorization"

        return response