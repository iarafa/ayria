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
    create_access_token, create_refresh_token,
    get_current_user,
)
import models
import schemas


async def _user_to_response(user: models.User, db: AsyncSession) -> schemas.UserResponse:
    """Helper: monta UserResponse com dados do plano carregados (async-safe)"""
    plan = None
    if user.selected_plan_id:
        from sqlalchemy import select as sa_select
        plan_res = await db.execute(
            sa_select(models.Plan).where(models.Plan.id == user.selected_plan_id)
        )
        plan = plan_res.scalar_one_or_none()
    data = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "role": user.role,
        "onboarding_status": user.onboarding_status or "pending",
        "profile_status": user.profile_status or "pending",
        "numerology_data": user.numerology_data,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "selected_plan_id": user.selected_plan_id,
        "selected_plan_slug": plan.slug if plan else None,
        "selected_plan_name": plan.name if plan else None,
        "credit_balance": user.credit_balance or 0,
        "credit_status": user.credit_status or "inactive",
        "plan_selected_at": user.plan_selected_at,
        "billing_status": user.billing_status or "billing_not_enabled",
        "credits_last_granted_at": user.credits_last_granted_at,
    }
    return schemas.UserResponse(**data)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ⚠️ Rate-limit por IP no /register foi REMOVIDO em 04/07/2026 por decisão do Rafael
# (estava travando testes com 15+ usuários no mesmo IP da LAN).
# Proteção contra criação em massa agora é por email único + captcha/validação no front.


@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
async def register(payload: schemas.UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    """Registra novo usuário + concede créditos do plano escolhido"""
    # Verifica email duplicado
    existing = await db.execute(
        select(models.User).where(models.User.email == payload.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    # Plan_slug é OBRIGATÓRIO para novos usuários (exceto admin criando via /admin/users)
    if not payload.plan_slug:
        raise HTTPException(
            status_code=400,
            detail="Escolha um plano (plan_slug: basico | intermediario | premium)",
        )

    # Busca plano
    from services.credit_service import get_plan_by_slug, grant_initial_credits
    plan = await get_plan_by_slug(db, payload.plan_slug)
    if not plan:
        raise HTTPException(
            status_code=400,
            detail=f"Plano '{payload.plan_slug}' não encontrado ou inativo",
        )

    # Cria usuário (com campos de billing zerados — grant vai preencher)
    user = models.User(
        id=uuid.uuid4(),
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="user",
        is_active=True,
        is_verified=False,
        onboarding_status="pending",
        credit_balance=0,
        credit_status="inactive",
        billing_status="billing_not_enabled",
    )
    db.add(user)
    await db.flush()  # garante user.id antes de criar profile

    # Cria perfil vazio
    profile = models.UserProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        attributes={},
        onboarding_completed=False,
    )
    db.add(profile)

    # Concede créditos do plano (idempotente — protege contra retry do front)
    await grant_initial_credits(
        db=db,
        user=user,
        plan=plan,
        description=f"Créditos iniciais concedidos no cadastro conforme plano {plan.name}",
        reference_type="user_register",
        reference_id=str(user.id),
    )

    await db.commit()
    await db.refresh(user)

    # Gera token
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token(str(user.id), user.role)

    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        user=await _user_to_response(user, db),
    )


@router.post("/login", response_model=schemas.TokenResponse)
async def login(payload: schemas.UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """Login com email + senha"""
    # ⚠️ RATE LIMIT REMOVIDO (Rafael cobrou: em produção, login nunca deve bloquear o user)
    # O bloco abaixo estava implementando um rate-limit por IP que travava
    # o desenvolvedor em testes. Login não deve ter rate-limit duro - cabe
    # à infra (CDN / WAF / fail2ban) proteger contra brute-force.
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
    
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token(str(user.id), user.role)

    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        user=await _user_to_response(user, db),
    )


@router.get("/me", response_model=schemas.UserResponse)
async def get_me(user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Retorna dados do usuário logado"""
    return await _user_to_response(user, db)


class RefreshRequest(BaseModel):
    """POST /api/auth/refresh — renovar access token usando refresh"""
    refresh_token: str


@router.post("/refresh", response_model=schemas.TokenResponse)
async def refresh_access_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Troca refresh_token (7d) por novo access_token (24h)."""
    from utils.security import decode_token

    token_data = decode_token(payload.refresh_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado")

    # 🆕 Verifica que é refresh token, não access token forjado
    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token não é um refresh token")

    user_id = token_data.get("sub")
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo")

    new_access = create_access_token({"sub": str(user.id), "role": user.role})
    new_refresh = create_refresh_token(str(user.id), user.role)

    return schemas.TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        user=await _user_to_response(user, db),
    )


class ProfileUpdateRequest(BaseModel):
    """PATCH /api/auth/me — atualizar dados do próprio user"""
    full_name: str | None = None
    avatar_url: str | None = None


class PasswordChangeRequest(BaseModel):
    """PATCH /api/auth/me/password — trocar propria senha"""
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


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
    return await _user_to_response(user, db)


@router.patch("/me/password", status_code=200)
async def change_my_password(
    payload: PasswordChangeRequest,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """🆕 User troca a própria senha (precisa da senha atual como confirmação)."""
    from utils.security import verify_password, hash_password

    # 1. Verifica senha atual
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Senha atual incorreta."
        )

    # 2. Não pode repetir a mesma senha
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(
            status_code=400,
            detail="A nova senha não pode ser igual à atual."
        )

    # 3. Atualiza
    user.password_hash = hash_password(payload.new_password)
    user.updated_at = datetime.utcnow()
    await db.commit()

    return {"message": "Senha alterada com sucesso. Faça login novamente."}


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
    return await _user_to_response(user, db)
