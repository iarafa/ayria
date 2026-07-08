"""
AYRIA - FastAPI Application Principal
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# 🆕 Configuração central de logging (07/07/2026)
# Garante que TODOS os logs (uvicorn, routers, error handlers) vão pro arquivo persistente
LOG_DIR = os.getenv("AYRIA_LOG_DIR", "/app/logs")
LOG_FILE = os.path.join(LOG_DIR, "ayria.log")
os.makedirs(LOG_DIR, exist_ok=True)

# Formato
_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

# Root logger (captura tudo)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Handler arquivo (10MB x 5 backups)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10_000_000, backupCount=5, encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(_FMT, _DATEFMT))

# Handler stdout (também aparece em logs do Coolify)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(logging.Formatter(_FMT, _DATEFMT))

# Remove handlers duplicados (caso reload)
root_logger.handlers.clear()
root_logger.addHandler(file_handler)
root_logger.addHandler(stdout_handler)

# Força logs do uvicorn a passar pelo nosso handler
logging.getLogger("uvicorn").handlers = root_logger.handlers
logging.getLogger("uvicorn.error").handlers = root_logger.handlers
logging.getLogger("uvicorn.access").handlers = root_logger.handlers
logging.getLogger("fastapi").handlers = root_logger.handlers

logger = logging.getLogger(__name__)
logger.info("=" * 60)
logger.info("🌙 AYRIA iniciando - sistema de log ativo em %s", LOG_FILE)
logger.info("=" * 60)

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import settings, get_db, init_db
import models  # noqa - importa models pro create_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup + shutdown"""
    print("🌙 AYRIA iniciando...")
    print(f"   Environment: {settings.ENVIRONMENT}")
    print(f"   Database: {settings.DATABASE_URL.split('@')[-1]}")
    print(f"   Qdrant: {settings.QDRANT_URL}")
    print(f"   IA: {settings.AI_MODEL} via {settings.AI_BASE_URL}")
    
    # Em dev, cria tabelas se não existirem (Alembic em prod)
    if settings.ENVIRONMENT == "development":
        try:
            await init_db()
            print("   ✅ Database tables ensured")
        except Exception as e:
            print(f"   ⚠️  Database init warning: {e}")

    # 🆕 AUTO-MIGRATION: aplica migrations .sql pendentes em TODO startup
    # Resolve o problema de Coolify subir com migration não aplicada
    try:
        from database import AsyncSessionLocal
        from services.migrator import run_pending_migrations
        async with AsyncSessionLocal() as db:
            migration_stats = await run_pending_migrations(db)
            if migration_stats["applied"]:
                print(f"   🔄 Migrations aplicadas: {migration_stats['applied']}")
            else:
                print(f"   ✅ Migrations: {len(migration_stats['skipped'])} já aplicadas, nenhuma pendente")
    except Exception as e:
        print(f"   ❌ ERRO nas migrations: {e}")
        # Falha nas migrations é CRÍTICA — não sobe o backend sem banco consistente
        raise SystemExit(f"Migration failed: {e}")

    # Seed: garante que os 3 planos oficiais existem (idempotente)
    try:
        from database import AsyncSessionLocal
        from sqlalchemy import select
        import models
        async with AsyncSessionLocal() as db:
            existing_slugs = set(
                (await db.execute(select(models.Plan.slug))).scalars().all()
            )
            official = [
                ("Básico", "basico", 100, 29.90),
                ("Intermediário", "intermediario", 500, 59.90),
                ("Premium", "premium", 1000, 99.90),
            ]
            added = 0
            for name, slug, credits, price in official:
                if slug not in existing_slugs:
                    db.add(models.Plan(
                        name=name, slug=slug, credits=credits,
                        price_brl=price, active=True,
                    ))
                    added += 1
            if added:
                await db.commit()
                print(f"   ✅ Seed: {added} plano(s) criado(s)")
            else:
                print(f"   ✅ Seed: 3 planos já presentes")
    except Exception as e:
        print(f"   ⚠️  Seed planos warning: {e}")
    
    print("✨ AYRIA online")
    yield
    
    print("🌙 AYRIA encerrando...")


app = FastAPI(
    title="AYRIA API",
    description="Plataforma de IA para autoconhecimento, psicologia e numerologia",
    version="1.0.0",
    # 🆕 Segurança: docs abertos só em dev. Em prod, desabilita pra não vazar superfície de ataque.
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan,
)

# CORS
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🆕 Request logger middleware (07/07/2026)
# Loga TODA requisição: método, path, status, duração, user_id (se autenticado)
import time
import uuid as _uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(_uuid.uuid4())[:8]
        start = time.time()
        method = request.method
        path = request.url.path
        # Captura user_id do JWT se presente
        user_id = "anon"
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            try:
                from jose import jwt as _jwt
                from database import settings as _s
                payload = _jwt.get_unverified_claims(auth.split(" ", 1)[1])
                user_id = str(payload.get("sub", "anon"))[:12]
            except Exception:
                pass
        try:
            response = await call_next(request)
            duration_ms = int((time.time() - start) * 1000)
            status = response.status_code
            level = logging.WARNING if status >= 400 else logging.INFO
            logging.getLogger("ayria.request").log(
                level,
                f"[{request_id}] {method} {path} → {status} ({duration_ms}ms) user={user_id}",
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            duration_ms = int((time.time() - start) * 1000)
            logging.getLogger("ayria.request").exception(
                f"[{request_id}] {method} {path} → EXCEPTION ({duration_ms}ms) user={user_id}: {type(exc).__name__}: {exc}"
            )
            raise

app.add_middleware(RequestLoggerMiddleware)

# 🆕 Exception handler global (07/07/2026)
# Garante que QUALQUER exceção não tratada apareça no log
from fastapi.responses import JSONResponse as _JSONResponse

@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    rid = getattr(request.state, "request_id", "?")
    logging.getLogger("ayria.error").exception(
        f"❌ UNCAUGHT [{rid}] {request.method} {request.url.path}: {type(exc).__name__}: {exc}"
    )
    return _JSONResponse(
        status_code=500,
        content={"detail": f"Erro interno do servidor: {type(exc).__name__}: {str(exc)[:200]}"},
        headers={"X-Request-ID": rid},
    )

# Audit middleware (registra acoes no audit_log)
from middleware.audit import AuditMiddleware
app.add_middleware(AuditMiddleware)

# No-cache middleware (impede cache de dados sensíveis no navegador)
from middleware.no_cache import NoCacheAPIMiddleware
app.add_middleware(NoCacheAPIMiddleware)

# 🆕 Security headers middleware (CSP, X-Frame-Options, HSTS, etc.)
from middleware.security_headers import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)


# ============================================================
# Health & Info
# ============================================================
@app.get("/")
async def root():
    return {
        "app": "AYRIA",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    """Health check - verifica DB"""
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)[:100]}"
    
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/api/v1/info")
async def info():
    """Info pública da AYRIA"""
    return {
        "name": "AYRIA",
        "tagline": "Plataforma de IA para autoconhecimento",
        "features": [
            "Chat com IA personalizado",
            "Memória de longo prazo",
            "Base de conhecimento treinável",
            "Onboarding inteligente",
            "Numerologia",
        ],
        "stack": {
            "backend": "FastAPI",
            "database": "PostgreSQL",
            "vector": "Qdrant",
            "storage": "Azure Blob",
            "ai": "Minimax / OpenAI",
        },
    }


# Routers
from routers import auth, onboarding, chats, chat, admin, memory, training, credits, supervisor, spiritual, debug_log
app.include_router(auth.router)
app.include_router(onboarding.router)
app.include_router(chats.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(debug_log.router)
app.include_router(memory.router)
app.include_router(training.router)
app.include_router(credits.router)
app.include_router(supervisor.router)
app.include_router(spiritual.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
