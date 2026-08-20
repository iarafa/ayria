"""
AYRIA - Rate Limiter (slowapi)

Limita requests por user_id (extraído do JWT). Usado em:
- /api/chat/message: 30 msgs/minuto (evita spam)
- /api/auth/resend-verification: 1/minuto (já existia, mas agora centralizado)

Storage: in-memory (suficiente para VPS single-instance).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

# Key function: usa user_id do JWT se autenticado, senão IP
def get_user_or_ip_key(request: Request) -> str:
    """
    Extrai user_id do JWT (Authorization header) pra usar como chave.
    Se não autenticado, usa IP.
    """
    try:
        from jose import jwt as _jwt
        from database import settings as _s
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            payload = _jwt.get_unverified_claims(auth.split(" ", 1)[1])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
    except Exception:
        pass
    return f"ip:{get_remote_address(request)}"


# Limiter global
limiter = Limiter(key_func=get_user_or_ip_key, storage_uri="memory://")
