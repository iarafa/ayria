"""
AYRIA - Configuração do Banco de Dados PostgreSQL
Usa SQLAlchemy 2.0 async + Alembic para migrations
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine
from pydantic_settings import BaseSettings
from typing import AsyncGenerator
import os


class Settings(BaseSettings):
    """Configurações via .env"""
    DATABASE_URL: str = "postgresql+asyncpg://ayria:ayria_dev@localhost:5432/ayria"
    DATABASE_URL_SYNC: str = "postgresql://ayria:ayria_dev@localhost:5432/ayria"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    
    MINIMAX_API_KEY: str = ""
    MINIMAX_BASE_URL: str = "https://api.minimax.io/v1"
    MINIMAX_MODEL: str = "MiniMax-M2.7"
    
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER: str = "ayria-docs"
    
    JWT_SECRET: str = "CHANGE_ME_AYRIA_DEV_ONLY"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://192.168.3.37:5173"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


# Engine assíncrono (principal)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.ENVIRONMENT == "development"),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Engine síncrono (Alembic migrations)
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)


# Base para os models
class Base(DeclarativeBase):
    """Base SQLAlchemy 2.0 para todos os models"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para injetar session nos endpoints FastAPI"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Cria tabelas (apenas dev - produção usa Alembic)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
