"""
AYRIA - FastAPI Application Principal
"""
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
