"""
AYRIA - Auth Router
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
"""
from fastapi import APIRouter, Depends, HTTPException, status
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
async def login(payload: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    """Login com email + senha"""
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
