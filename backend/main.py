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
    print(f"   IA: {settings.MINIMAX_MODEL}")
    
    # Em dev, cria tabelas se não existirem (Alembic em prod)
    if settings.ENVIRONMENT == "development":
        try:
            await init_db()
            print("   ✅ Database tables ensured")
        except Exception as e:
            print(f"   ⚠️  Database init warning: {e}")
    
    print("✨ AYRIA online")
    yield
    
    print("🌙 AYRIA encerrando...")


app = FastAPI(
    title="AYRIA API",
    description="Plataforma de IA para autoconhecimento, psicologia e numerologia",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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


# Routers (vou adicionar nas próximas fases)
# from routers import auth, users, chats, admin, onboarding
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
# app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
# app.include_router(onboarding.router, prefix="/api/v1/onboarding", tags=["onboarding"])
# app.include_router(chats.router, prefix="/api/v1/chats", tags=["chats"])
# app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
