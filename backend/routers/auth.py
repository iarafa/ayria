"""
AYRIA - Auth Router
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
PATCH /api/auth/me         (atualizar nome/avatar_url)
POST /api/auth/me/avatar   (upload de foto)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import uuid

from pydantic import BaseModel, EmailStr, Field
from database import get_db, settings
from utils.security import (
    hash_password, verify_password,
    create_access_token, get_current_user,
)
import models
import schemas

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Rate limiting simples in-memory (production: use Redis)
from collections import defaultdict
import time as _time
_login_attempts = defaultdict(list)
_register_attempts = defaultdict(list)
RATE_LIMIT_LOGIN = 5  # max 5 tentativas
RATE_LIMIT_WINDOW = 60  # por 60 segundos


@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
async def register(payload: schemas.UserRegister, db: AsyncSession = Depends(get_db)):
    """Registra novo usuário"""
    # Verifica email duplicado
    existing = await db.execute(
        select(models.User).where(models.User.email == payload.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Cria usuário
    user = models.User(
        id=uuid.uuid4(),
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="user",
        is_active=True,
        is_verified=False,
        onboarding_status="pending",
    )
    db.add(user)
    
    # Cria perfil vazio
    profile = models.UserProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        attributes={},
        onboarding_completed=False,
    )
    db.add(profile)
    
    await db.commit()
    await db.refresh(user)
    
    # Gera token
    token = create_access_token({"sub": str(user.id), "role": user.role})
    
    return schemas.TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        user=schemas.UserResponse.model_validate(user),
    )


@router.post("/login", response_model=schemas.TokenResponse)
async def login(payload: schemas.UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """Login com email + senha"""
    # Rate limit por IP
    ip = request.client.host if request.client else "unknown"
    now = _time.time()
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_login_attempts[ip]) >= RATE_LIMIT_LOGIN:
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas de login. Tente em {RATE_LIMIT_WINDOW}s.",
        )
    _login_attempts[ip].append(now)
    result = await db.execute(
        select(models.User).where(models.User.email == payload.email)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuário desativado")
    
    # Atualiza last_login
    user.last_login_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    
    token = create_access_token({"sub": str(user.id), "role": user.role})
    
    return schemas.TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        user=schemas.UserResponse.model_validate(user),
    )


@router.get("/me", response_model=schemas.UserResponse)
async def get_me(user: models.User = Depends(get_current_user)):
    """Retorna dados do usuário logado"""
    return schemas.UserResponse.model_validate(user)


class ProfileUpdateRequest(BaseModel):
    """PATCH /api/auth/me — atualizar dados do próprio user"""
    full_name: str | None = None
    avatar_url: str | None = None


@router.patch("/me", response_model=schemas.UserResponse)
async def update_me(
    payload: ProfileUpdateRequest,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Atualiza nome e/ou avatar_url do usuário logado"""
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()[:255] if payload.full_name.strip() else None
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url.strip()[:500] if payload.avatar_url.strip() else None
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return schemas.UserResponse.model_validate(user)


@router.post("/me/avatar", response_model=schemas.UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload de foto de perfil. Salva no Azure Blob Storage e retorna URL pública."""
    # Valida tipo MIME
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo precisa ser uma imagem (JPEG, PNG, GIF, WebP)"
        )

    # Limita tamanho (5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Imagem deve ter no máximo 5MB"
        )

    # Salva no Azure Blob Storage
    try:
        from services.storage_service import upload_user_avatar
        avatar_url = await upload_user_avatar(
            user_id=str(user.id),
            filename=file.filename or "avatar.jpg",
            content_type=file.content_type,
            data=contents,
            previous_url=user.avatar_url,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar foto: {str(e)}"
        )

    user.avatar_url = avatar_url
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return schemas.UserResponse.model_validate(user)
