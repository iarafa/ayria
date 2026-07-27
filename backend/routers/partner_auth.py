"""
🆕 26/07/2026 22:43 — AUTENTICAÇÃO DO PARCEIRO
Parceiro recebe email/senha quando criado pelo admin.
Ele entra com credenciais em /partner/login → token próprio → /partner/:id
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Partner, User
from utils.security import (
    create_access_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger("partner_auth")

router = APIRouter(tags=["partner_auth"])


# ============================================================
# SCHEMAS
# ============================================================
class PartnerLoginRequest(BaseModel):
    email: str
    password: str


class PartnerLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    partner_id: str
    partner_name: str
    partner_email: str
    must_change_password: bool


class PartnerChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ============================================================
# DEPENDENCY: get current partner from JWT
# Token payload: {sub: partner_id, type: "partner", exp: ...}
# ============================================================
oauth2_partner_scheme = OAuth2PasswordBearer(tokenUrl="/api/partner/login", auto_error=False)


async def _decode_partner_token(token: str) -> Partner:
    """Decodifica token JWT de parceiro sem tocar no DB."""
    from jose import JWTError, jwt
    from utils.security import SECRET_KEY, ALGORITHM
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "partner":
            raise HTTPException(401, "Token não é de parceiro")
        partner_id = payload.get("sub")
        if not partner_id:
            raise HTTPException(401, "Token sem identificação")
    except JWTError:
        raise HTTPException(401, "Token inválido ou expirado")

    from uuid import UUID
    try:
        return UUID(partner_id)
    except ValueError:
        raise HTTPException(401, "Token inválido")


async def get_current_partner(
    token: str = Depends(oauth2_partner_scheme),
    db: AsyncSession = Depends(get_db),
) -> Partner:
    """Valida JWT de parceiro e retorna o Partner. (Raises 401 se inválido.)"""
    if not token:
        raise HTTPException(401, "Token não informado")
    pid = await _decode_partner_token(token)
    partner = await db.get(Partner, pid)
    if not partner:
        raise HTTPException(401, "Parceiro não encontrado")
    if not partner.active:
        raise HTTPException(403, "Parceiro desativado. Fale com o admin.")
    return partner


async def get_current_partner_optional(
    token: Optional[str] = Depends(oauth2_partner_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[Partner]:
    """Tenta autenticar como parceiro. Retorna None se falhar."""
    if not token:
        return None
    try:
        pid = await _decode_partner_token(token)
        partner = await db.get(Partner, pid)
        if not partner or not partner.active:
            return None
        return partner
    except HTTPException:
        return None


# ============================================================
# POST /api/partner/login
# ============================================================
@router.post("/api/partner/login", response_model=PartnerLoginResponse)
async def partner_login(req: PartnerLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Parceiro entra com email + senha.
    Retorna JWT próprio (separado do JWT de user/admin).
    Se must_change_password=true → frontend força tela de troca antes do portal.
    """
    # Case-insensitive email lookup
    email = req.email.strip().lower()
    result = await db.execute(select(Partner).where(Partner.email.ilike(email)))
    partner = result.scalar_one_or_none()

    if not partner or not partner.password_hash:
        # Mensagem genérica pra não vazar quais emails existem
        raise HTTPException(401, "Email ou senha incorretos")

    if not partner.active:
        raise HTTPException(403, "Parceiro desativado. Fale com o admin.")

    if not verify_password(req.password, partner.password_hash):
        raise HTTPException(401, "Email ou senha incorretos")

    # Update last_login_at
    partner.last_login_at = datetime.utcnow()
    await db.commit()

    # Token específico de parceiro (type=partner)
    access_token = create_access_token(
        data={"sub": str(partner.id), "type": "partner"},
        expires_delta=timedelta(days=7),  # 7 dias pra parceiro (não usa o celular toda hora)
    )

    logger.info(f"partner_login OK: {partner.email} (must_change={partner.must_change_password})")

    return PartnerLoginResponse(
        access_token=access_token,
        partner_id=str(partner.id),
        partner_name=partner.name,
        partner_email=partner.email,
        must_change_password=partner.must_change_password or False,
    )


# ============================================================
# POST /api/partner/me/change-password
# ============================================================
@router.post("/api/partner/me/change-password")
async def partner_change_password(
    req: PartnerChangePasswordRequest,
    partner: Partner = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    """Parceiro troca a própria senha. Limpa flag must_change_password."""
    if not verify_password(req.current_password, partner.password_hash):
        raise HTTPException(400, "Senha atual incorreta")

    if len(req.new_password) < 6:
        raise HTTPException(400, "Nova senha precisa ter no mínimo 6 caracteres")

    partner.password_hash = hash_password(req.new_password)
    partner.must_change_password = False
    partner.updated_at = datetime.utcnow()
    await db.commit()

    logger.info(f"partner_password_changed: {partner.email}")
    return {"ok": True, "message": "Senha alterada com sucesso"}


# ============================================================
# GET /api/partner/me  — info do parceiro autenticado
# ============================================================
@router.get("/api/partner/me")
async def partner_me(partner: Partner = Depends(get_current_partner)):
    """Retorna dados do parceiro logado (sem senha)."""
    return {
        "id": str(partner.id),
        "name": partner.name,
        "email": partner.email,
        "phone": partner.phone,
        "must_change_password": partner.must_change_password or False,
        "last_login_at": partner.last_login_at.isoformat() if partner.last_login_at else None,
    }