"""
AYRIA - Security Utils
JWT + bcrypt password hashing
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import settings, get_db
import models

# bcrypt context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT bearer
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash senha com bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica senha contra hash"""
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, token_type: str = "access") -> str:
    """Cria JWT token (access ou refresh)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": token_type})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str, role: str) -> str:
    """Cria refresh token (7 dias). Usado pra renovar access token sem login."""
    return create_access_token(
        data={"sub": user_id, "role": role},
        expires_delta=timedelta(days=7),
        token_type="refresh",
    )


def decode_token(token: str) -> Optional[dict]:
    """Decodifica JWT"""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> models.User:
    """Dependency: pega usuário atual via JWT"""
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuário desativado")

    # Check de bloqueio (admin controla acesso manual)
    if user.blocked_at is not None:
        if user.blocked_until is None:
            # Permanente
            raise HTTPException(
                status_code=403,
                detail=f"Acesso bloqueado permanentemente. Motivo: {user.block_reason or 'sem motivo'}",
            )
        if user.blocked_until > datetime.now(timezone.utc):
            # Temporário, ainda bloqueado
            raise HTTPException(
                status_code=403,
                detail=f"Acesso bloqueado até {user.blocked_until.isoformat()}. Motivo: {user.block_reason or 'sem motivo'}",
            )
        # blocked_until já passou, limpar automaticamente (auto-unblock)
        user.blocked_until = None
        user.blocked_at = None
        user.blocked_by = None
        user.block_reason = None
        await db.commit()

    return user


async def require_admin(
    user: models.User = Depends(get_current_user),
) -> models.User:
    """Dependency: exige role admin/SUPER_ADMIN"""
    if user.role not in ("admin", "SUPER_ADMIN"):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user
