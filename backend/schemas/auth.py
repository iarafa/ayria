"""
Schemas de autenticação: registro, login, tokens, verificação de email.
"""
from typing import Optional
from pydantic import BaseModel, Field

from ._base import uuid
from .user import UserResponse  # forward ref resolvido em __init__


# ============================================================
# AUTH
# ============================================================
class UserRegister(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)  # min 8 chars
    full_name: Optional[str] = None
    role: Optional[str] = "user"  # admin pode passar SUPER_ADMIN na criação
    plan_slug: Optional[str] = None  # basico|intermediario|premium — OPCIONAL em /auth/register (19/07/2026)


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None  # 7 dias, usado pra renovar
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


# ============ Email Verification (07/07/2026) ============

class RegisterResponse(BaseModel):
    """Resposta do /register após verificação de email implementada.
    NÃO retorna access_token — só após user clicar no link do email."""
    user: "UserResponse"
    message: str
    verification_sent: bool
    email_error: Optional[str] = None


class VerifyEmailResponse(BaseModel):
    success: bool
    message: str
    already_verified: bool = False


class ResendVerificationResponse(BaseModel):
    sent: bool
    message: str
    already_verified: bool = False
