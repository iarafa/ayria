"""
AYRIA - Security Utils
JWT + bcrypt password hashing
"""
from datetime import datetime, timedelta
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


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


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
    
    return user


async def require_admin(
    user: models.User = Depends(get_current_user),
) -> models.User:
    """Dependency: exige role admin/SUPER_ADMIN"""
    if user.role not in ("admin", "SUPER_ADMIN"):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user
