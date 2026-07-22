"""
AYRIA - Admin Router
GET    /api/admin/users
POST   /api/admin/users            - Cria user (admin pode passar role=admin)
PUT    /api/admin/users/{id}        - Edita nome / is_active
DELETE /api/admin/users/{id}        - Exclui user
GET    /api/admin/knowledge/list
POST   /api/admin/knowledge/upload
DELETE /api/admin/knowledge/{id}
GET    /api/admin/onboarding/config
PUT    /api/admin/onboarding/config
GET    /api/admin/attributes
POST   /api/admin/attributes
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, text
import uuid
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import json

from database import get_db
from utils.security import require_admin, hash_password
from services.storage_service import storage_service
from services import credit_service
from services.prompt_selector import PROMPTS_DIR
import models
import schemas

router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = logging.getLogger(__name__)


# ============================================================
# USERS
# ============================================================
@router.get("/users", response_model=schemas.AdminUsersListResponse)
async def list_users(
    search: Optional[str] = Query(None, description="Busca em email e full_name (case-insensitive)"),
    status: str = Query("all", description="Filtro de status: all | active | inactive | blocked | pending"),
    role_filter: str = Query("users_only", description="Filtro de role: 'users_only' (exclui SUPER_ADMIN/admin — default da aba Usuários) | 'all' (inclui todos, usado pela aba Admin)"),
    page: int = Query(1, ge=1, description="Página (1-based)"),
    page_size: int = Query(25, ge=1, le=100, description="Itens por página (max 100)"),
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lista usuários (admin) - com busca, filtros de status e paginação.

    Suporta:
    - search:     substring em email OU full_name (case-insensitive, %LIKE%)
    - status:     all | active (is_active=true) | inactive | blocked (blocked_until IS NOT NULL)
                  | pending (onboarding_status='pending')
    - role_filter: users_only (exclui admin/SUPER_ADMIN, default) | all (inclui todos)
                   A aba 'Usuários' do admin só mostra clientes; admins ficam na aba 'Configurações'.
    - page:       1-based, default 1
    - page_size:  default 25, max 100
    """
    # ===== Query base =====
    base_q = select(models.User)

    # 19/07/2026: aba 'Usuários' do admin NÃO mostra administradores do sistema.
    # Por padrão role_filter='users_only' — exclui SUPER_ADMIN e admin.
    if role_filter == "users_only":
        base_q = base_q.where(models.User.role == "user")
    # role_filter='all' → sem filtro de role

    if search:
        pat = f"%{search.lower()}%"
        base_q = base_q.where(
            or_(
                func.lower(models.User.email).like(pat),
                func.lower(func.coalesce(models.User.full_name, "")).like(pat),
            )
        )

    if status == "active":
        base_q = base_q.where(models.User.is_active.is_(True))
    elif status == "inactive":
        base_q = base_q.where(models.User.is_active.is_(False))
    elif status == "blocked":
        base_q = base_q.where(models.User.blocked_until.isnot(None))
    elif status == "pending":
        base_q = base_q.where(models.User.onboarding_status == "pending")
    # 'all' = sem filtro

    # ===== Count total =====
    total = await db.scalar(
        select(func.count()).select_from(base_q.subquery())
    ) or 0

    # ===== Page =====
    offset = (page - 1) * page_size
    page_q = base_q.order_by(models.User.created_at.desc()).offset(offset).limit(page_size)
    users = (await db.execute(page_q)).scalars().all()

    # ===== Hidrata plano + count pra cada user =====
    items: list[schemas.AdminUserResponse] = []
    for u in users:
        msg_count = await db.scalar(
            select(func.count(models.Message.id)).where(models.Message.user_id == u.id)
        ) or 0

        plan = None
        if u.selected_plan_id:
            plan = await db.scalar(
                select(models.Plan).where(models.Plan.id == u.selected_plan_id)
            )

        items.append(schemas.AdminUserResponse(
            id=u.id, email=u.email, full_name=u.full_name, role=u.role,
            is_active=u.is_active, onboarding_status=u.onboarding_status or "pending",
            created_at=u.created_at, last_login_at=u.last_login_at,
            message_count=msg_count,
            selected_plan_id=u.selected_plan_id,
            selected_plan_slug=plan.slug if plan else None,
            selected_plan_name=plan.name if plan else None,
            credit_balance=u.credit_balance or 0,
            credit_status=u.credit_status or "inactive",
            plan_selected_at=u.plan_selected_at,
            billing_status=u.billing_status or "billing_not_enabled",
            credits_last_granted_at=u.credits_last_granted_at,
            blocked_until=u.blocked_until, blocked_at=u.blocked_at,
            blocked_by=u.blocked_by, block_reason=u.block_reason,
        ))

    total_pages = (total + page_size - 1) // page_size  # ceil

    return schemas.AdminUsersListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/users", response_model=schemas.AdminUserResponse, status_code=201)
async def create_user(
    payload: schemas.UserRegister,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin cria novo usuário. Pode passar role=SUPER_ADMIN no payload se quiser criar admin.
    Aceita plan_slug (default: basico) - concede créditos iniciais via service idempotente."""
    existing = await db.execute(
        select(models.User).where(models.User.email == payload.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    # Admin pode escolher role no momento da criação
    requested_role = getattr(payload, "role", "user")
    if requested_role not in ("user", "SUPER_ADMIN"):
        requested_role = "user"

    # Plano: admin cria com plano padrão (basico) se não informar
    plan_slug = getattr(payload, "plan_slug", None) or "basico"
    plan = await credit_service.get_plan_by_slug(db, plan_slug)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Plano '{plan_slug}' não encontrado")

    user = models.User(
        id=uuid.uuid4(),
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=requested_role,  # Admin define role direto na criação (sem promoção depois)
        is_active=True,
        is_verified=True,  # Admin cria já verificado
        onboarding_status="pending",
        selected_plan_id=plan.id,
        plan_selected_at=datetime.utcnow(),
        credit_status="active",
        billing_status="billing_not_enabled",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Concede créditos iniciais (idempotente - se já existir grant, não duplica)
    await credit_service.grant_initial_credits(
        db=db,
        user=user,
        plan=plan,
        description=f"Créditos iniciais concedidos pelo admin ({admin.email}) conforme plano {plan.name}",
    )
    await db.refresh(user)

    return schemas.AdminUserResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role, is_active=user.is_active,
        onboarding_status=user.onboarding_status or "pending",
        created_at=user.created_at, last_login_at=user.last_login_at,
        message_count=0,
        selected_plan_id=user.selected_plan_id,
        selected_plan_slug=plan.slug,
        selected_plan_name=plan.name,
        credit_balance=user.credit_balance or 0,
        credit_status=user.credit_status or "inactive",
        plan_selected_at=user.plan_selected_at,
        billing_status=user.billing_status or "billing_not_enabled",
        credits_last_granted_at=user.credits_last_granted_at,
    )


@router.put("/users/{user_id}", response_model=schemas.AdminUserResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: schemas.UserUpdate,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Edita nome, is_active OU troca plano de um usuário (NÃO muda role).
    Se selected_plan_slug for informado e diferente do atual, troca o plano +
    registra transaction (delta = credits do novo plano - saldo atual, pode ser +/-)."""
    res = await db.execute(select(models.User).where(models.User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Você não pode editar a si mesmo")

    # Editar apenas campos permitidos (NÃO role)
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active

    # Trocar plano se solicitado
    if payload.selected_plan_slug is not None:
        new_plan = await credit_service.get_plan_by_slug(db, payload.selected_plan_slug)
        if not new_plan:
            raise HTTPException(status_code=400, detail=f"Plano '{payload.selected_plan_slug}' não encontrado")

        # Verifica se mudou mesmo
        if user.selected_plan_id != new_plan.id:
            old_plan = None
            if user.selected_plan_id:
                old_res = await db.execute(
                    select(models.Plan).where(models.Plan.id == user.selected_plan_id)
                )
                old_plan = old_res.scalar_one_or_none()

            # Aplica delta: se novo plano tem mais créditos, adiciona; se tem menos, remove
            old_credits = old_plan.credits if old_plan else 0
            delta = new_plan.credits - old_credits  # pode ser negativo
            balance_before = user.credit_balance or 0
            new_balance = max(0, balance_before + delta)

            user.selected_plan_id = new_plan.id
            user.plan_selected_at = datetime.utcnow()
            user.credit_balance = new_balance

            # Registra transaction da troca
            tx = models.CreditTransaction(
                id=uuid.uuid4(),
                user_id=user.id,
                type="adjustment_manual",
                amount=delta,
                balance_before=balance_before,
                balance_after=new_balance,
                description=f"Plano trocado pelo admin: {old_plan.name if old_plan else 'nenhum'} → {new_plan.name}",
                reference_type="admin_plan_change",
                reference_id=str(admin.id),
                created_at=datetime.utcnow(),
            )
            db.add(tx)
            user.credits_last_granted_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user)

    # Carrega plano pra retornar info completa
    plan = None
    if user.selected_plan_id:
        plan_res = await db.execute(
            select(models.Plan).where(models.Plan.id == user.selected_plan_id)
        )
        plan = plan_res.scalar_one_or_none()

    return schemas.AdminUserResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role, is_active=user.is_active,
        onboarding_status=user.onboarding_status or "pending",
        created_at=user.created_at, last_login_at=user.last_login_at,
        message_count=0,
        selected_plan_id=user.selected_plan_id,
        selected_plan_slug=plan.slug if plan else None,
        selected_plan_name=plan.name if plan else None,
        credit_balance=user.credit_balance or 0,
        credit_status=user.credit_status or "inactive",
        plan_selected_at=user.plan_selected_at,
        billing_status=user.billing_status or "billing_not_enabled",
        credits_last_granted_at=user.credits_last_granted_at,
        blocked_until=user.blocked_until,
        blocked_at=user.blocked_at,
        blocked_by=user.blocked_by,
        block_reason=user.block_reason,
    )


@router.post("/users/{user_id}/block", response_model=schemas.AdminUserResponse)
async def block_user(
    user_id: uuid.UUID,
    payload: schemas.UserBlockRequest,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Bloqueia/desbloqueia um usuário.
    Duration:
        - "1h": bloqueia por 1 hora (blocked_until = now + 1h)
        - "24h": bloqueia por 24 horas
        - "permanent": bloqueia definitivamente (blocked_until = NULL, blocked_at = now)
        - "unblock": desbloqueia (limpa campos)

    Após bloqueio, usuário NÃO consegue mais:
        - Enviar mensagens (POST /chat retorna erro)
        - Fazer login (401)
        - Usar créditos
    """
    user_res = await db.execute(select(models.User).where(models.User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.role in ("admin", "SUPER_ADMIN"):
        raise HTTPException(status_code=403, detail="Não é possível bloquear admin")

    now = datetime.now(timezone.utc)
    duration = (payload.duration or "").lower()

    if duration == "unblock":
        # Restaurar is_active se foi desativado pelo block (DEVE checar ANTES de limpar)
        if not user.is_active and user.blocked_at is not None:
            user.is_active = True
        user.blocked_until = None
        user.blocked_at = None
        user.blocked_by = None
        user.block_reason = None
        logger.info(f"👤 User {user.email} UNBLOCKED by admin {admin.email}")
    elif duration == "1h":
        user.blocked_at = now
        user.blocked_until = now + timedelta(hours=1)
        user.blocked_by = admin.id
        user.block_reason = payload.reason
        user.is_active = False
        logger.warning(f"🚫 User {user.email} BLOCKED 1h by {admin.email}: {payload.reason}")
    elif duration == "24h":
        user.blocked_at = now
        user.blocked_until = now + timedelta(hours=24)
        user.blocked_by = admin.id
        user.block_reason = payload.reason
        user.is_active = False
        logger.warning(f"🚫 User {user.email} BLOCKED 24h by {admin.email}: {payload.reason}")
    elif duration == "permanent":
        user.blocked_at = now
        user.blocked_until = None  # NULL = permanente
        user.blocked_by = admin.id
        user.block_reason = payload.reason
        user.is_active = False
        logger.warning(f"🚫⛔ User {user.email} BLOCKED PERMANENTLY by {admin.email}: {payload.reason}")
    else:
        raise HTTPException(status_code=400, detail=f"duration inválida: {payload.duration}")

    # Se já tinha análise pendente de supervisor, marca como resolvida
    open_alerts = await db.execute(
        select(models.SupervisorAlert).where(
            models.SupervisorAlert.user_id == user_id,
            models.SupervisorAlert.status.in_(["open", "acknowledged"])
        )
    )
    for a in open_alerts.scalars():
        a.status = "resolved"
        a.resolved_by = admin.id
        a.resolved_at = now
        if not a.resolution_notes:
            a.resolution_notes = f"Usuário bloqueado: {payload.duration} — {payload.reason or 'sem motivo'}"

    await db.commit()
    await db.refresh(user)

    plan = None
    if user.selected_plan_id:
        plan_res = await db.execute(
            select(models.Plan).where(models.Plan.id == user.selected_plan_id)
        )
        plan = plan_res.scalar_one_or_none()

    return schemas.AdminUserResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role, is_active=user.is_active,
        onboarding_status=user.onboarding_status or "pending",
        created_at=user.created_at, last_login_at=user.last_login_at,
        message_count=0,
        selected_plan_id=user.selected_plan_id,
        selected_plan_slug=plan.slug if plan else None,
        selected_plan_name=plan.name if plan else None,
        credit_balance=user.credit_balance or 0,
        credit_status=user.credit_status or "inactive",
        plan_selected_at=user.plan_selected_at,
        billing_status=user.billing_status or "billing_not_enabled",
        credits_last_granted_at=user.credits_last_granted_at,
        blocked_until=user.blocked_until,
        blocked_at=user.blocked_at,
        blocked_by=user.blocked_by,
        block_reason=user.block_reason,
    )


@router.post("/users/{user_id}/password", response_model=schemas.AdminUserResponse)
async def admin_change_password(
    user_id: uuid.UUID,
    payload: schemas.AdminChangePasswordRequest,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin reseta senha de um user (sem precisar da senha antiga).

    - Validação: senha mínima 8 caracteres (requisito do sistema)
    - Auditoria: loga quem mudou + motivo
    - Admin não pode resetar a própria senha aqui (usar endpoint normal)
    """
    # Validação de tamanho
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Senha deve ter no mínimo 8 caracteres.",
        )

    # Busca user
    user_res = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Safety: admin não pode resetar a própria senha por aqui
    if user.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Use o endpoint próprio (/api/auth/me/password) pra trocar SUA senha.",
        )

    # Verifica se tem outra conta admin (safety check: não deixar sistema sem admin)
    if user.role in ("admin", "SUPER_ADMIN") and user.id != admin.id:
        admins_res = await db.execute(
            select(func.count()).select_from(models.User).where(
                models.User.role.in_(["admin", "SUPER_ADMIN"]),
                models.User.is_active == True,
            )
        )
        admin_count = admins_res.scalar() or 0
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Bloqueado: é o único admin ativo. Crie outro admin antes.",
            )

    # Aplica nova senha
    old_hash_prefix = (user.password_hash or "")[:20]  # guarda prefixo pra auditoria
    user.password_hash = hash_password(payload.new_password)
    await db.commit()
    await db.refresh(user)

    # Loga auditoria (insere direto na tabela audit_log)
    try:
        from models import AuditLog
        ip = request.client.host if request.client else None
        audit_entry = AuditLog(
            id=uuid.uuid4(),
            user_id=admin.id,
            action="admin_password_reset",
            resource_type="user",
            resource_id=user.id,
            details={
                "target_email": user.email,
                "reason": payload.reason or "sem motivo",
            },
            ip_address=ip,
            user_agent="ayria-admin",
            created_at=datetime.now(timezone.utc),
        )
        db.add(audit_entry)
        await db.commit()
    except Exception as e:
        logger.warning(f"Falha ao registrar audit log (admin_password_reset): {e}")

    logger.warning(
        f"🔑 Admin {admin.email} resetou senha de {user.email} "
        f"(prefixo antigo: {old_hash_prefix!r}). Motivo: {payload.reason or 'N/A'}"
    )

    # Monta response igual ao list_users
    plan = None
    if user.selected_plan_id:
        plan_res = await db.execute(
            select(models.Plan).where(models.Plan.id == user.selected_plan_id)
        )
        plan = plan_res.scalar_one_or_none()

    message_count = await db.execute(
        select(func.count(models.Message.id))
        .join(models.Chat, models.Chat.id == models.Message.chat_id)
        .where(models.Chat.user_id == user.id)
    )
    message_count = message_count.scalar() or 0

    return schemas.AdminUserResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role, is_active=user.is_active,
        onboarding_status=user.onboarding_status or "pending",
        created_at=user.created_at, last_login_at=user.last_login_at,
        message_count=message_count,
        selected_plan_id=user.selected_plan_id,
        selected_plan_slug=plan.slug if plan else None,
        selected_plan_name=plan.name if plan else None,
        credit_balance=user.credit_balance or 0,
        credit_status=user.credit_status or "inactive",
        plan_selected_at=user.plan_selected_at,
        billing_status=user.billing_status or "billing_not_enabled",
        credits_last_granted_at=user.credits_last_granted_at,
        blocked_until=user.blocked_until,
        blocked_at=user.blocked_at,
        blocked_by=user.blocked_by,
        block_reason=user.block_reason,
    )


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Exclui um usuário E TODOS os dados dele (LGPD-style):
    - PostgreSQL: user_profiles, user_attributes, chats, messages
    - Qdrant: TODAS as memórias (memoria_episodica)
    - Audit log: preservado mas com user_id=NULL (pra auditoria)
    - Knowledge documents: NÃO deleta (são do admin, não do user)

    Safety:
    - Admin não pode excluir a si mesmo
    - Operação atômica - se algo falhar, ROLLBACK
    """
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir a si mesmo")

    res = await db.execute(select(models.User).where(models.User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    deleted_summary = {"pg": {}, "qdrant": 0}

    try:
        from sqlalchemy import text

        # 1. PostgreSQL: user_profiles (1:1)
        r = await db.execute(text("DELETE FROM user_profiles WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["user_profiles"] = r.rowcount

        # 2. PostgreSQL: user_attributes (valores dos atributos)
        r = await db.execute(text("DELETE FROM user_attributes WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["user_attributes"] = r.rowcount

        # 3. PostgreSQL: spiritual_preferences
        r = await db.execute(text("DELETE FROM spiritual_preferences WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["spiritual_preferences"] = r.rowcount

        # 4. PostgreSQL: credit_transactions (FK → users)
        r = await db.execute(text("DELETE FROM credit_transactions WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["credit_transactions"] = r.rowcount

        # 5. PostgreSQL: chat_question_skip (FK → users)
        r = await db.execute(text("DELETE FROM chat_question_skip WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["chat_question_skip"] = r.rowcount

        # 6. PostgreSQL: messages (via chats)
        r = await db.execute(text("DELETE FROM messages WHERE chat_id IN (SELECT id FROM chats WHERE user_id = :uid)"), {"uid": str(user_id)})
        deleted_summary["pg"]["messages"] = r.rowcount

        # 7. PostgreSQL: chats
        r = await db.execute(text("DELETE FROM chats WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["chats"] = r.rowcount

        # 8. Supervisor: alerts (referencia user_id + acknowledged_by/resolved_by)
        r = await db.execute(text("UPDATE supervisor_alerts SET user_id=NULL WHERE user_id=:uid"), {"uid": str(user_id)})
        r = await db.execute(text("UPDATE supervisor_alerts SET acknowledged_by=NULL WHERE acknowledged_by=:uid"), {"uid": str(user_id)})
        r = await db.execute(text("UPDATE supervisor_alerts SET resolved_by=NULL WHERE resolved_by=:uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["supervisor_alerts_anonymized"] = r.rowcount

        # 9. Supervisor: analysis + daily_summary + notes (NULL user_id pra preservar histórico)
        r = await db.execute(text("UPDATE supervisor_analysis SET user_id=NULL WHERE user_id=:uid"), {"uid": str(user_id)})
        r = await db.execute(text("UPDATE supervisor_daily_summary SET user_id=NULL WHERE user_id=:uid"), {"uid": str(user_id)})
        r = await db.execute(text("UPDATE user_supervisor_notes SET user_id=NULL WHERE user_id=:uid"), {"uid": str(user_id)})
        r = await db.execute(text("UPDATE user_supervisor_notes SET admin_id=NULL WHERE admin_id=:uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["supervisor_anonymized"] = r.rowcount

        # 10. user_alma (FK → users + created_by + approved_by)
        r = await db.execute(text("DELETE FROM user_alma WHERE user_id=:uid"), {"uid": str(user_id)})
        r = await db.execute(text("UPDATE user_alma SET created_by=NULL WHERE created_by=:uid"), {"uid": str(user_id)})
        r = await db.execute(text("UPDATE user_alma SET approved_by=NULL WHERE approved_by=:uid"), {"uid": str(user_id)})

        # 11. stripe_subscriptions + stripe_invoices (FK → users.ayria_user_id)
        try:
            r = await db.execute(text("DELETE FROM stripe_subscriptions WHERE ayria_user_id=:uid"), {"uid": str(user_id)})
            deleted_summary["pg"]["stripe_subscriptions"] = r.rowcount
        except Exception:
            pass
        try:
            r = await db.execute(text("DELETE FROM stripe_invoices WHERE ayria_user_id=:uid"), {"uid": str(user_id)})
            deleted_summary["pg"]["stripe_invoices"] = r.rowcount
        except Exception:
            pass

        # 12. Audit log: NULL user_id (preserva histórico, mas sem FK)
        # Não deleta - auditoria deve permanecer (LGPD permite pra fins de segurança)
        r = await db.execute(text("UPDATE audit_log SET user_id = NULL WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["audit_log_anonymized"] = r.rowcount

        # 13. Qdrant: TODAS as memórias do user
        from services.vector_service import vector_service
        deleted_summary["qdrant"] = await vector_service.delete_user_memories(str(user_id))

        # 7. Finalmente: deleta o user
        await db.delete(user)
        await db.commit()

        logger.info(
            f"✅ User {user.email} ({user_id}) excluído COMPLETAMENTE por admin {admin.email}. "
            f"Postgres: {deleted_summary['pg']}, Qdrant collections: {deleted_summary['qdrant']}"
        )
        return None

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Erro ao excluir user {user.email}: {e}")
        # 🆕 SECURITY: não vaza str(e) pro cliente (pode ter paths/SQL); só mensagem genérica
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao excluir usuário. Tente novamente ou contate o suporte."
        )


# ============================================================
# 🆕 ADMINS DO SISTEMA (19/07/2026)
# Gerenciamento separado dos usuários clientes.
# SUPER_ADMIN acessa em Configurações > Administradores do Sistema.
# Não aparecem na aba Usuários (que lista apenas clientes).
# ============================================================

class AdminCreateRequest(BaseModel):
    """Admin cria novo administrador (outro SUPER_ADMIN)."""
    email: str
    password: str = Field(..., min_length=8, description="Senha mínima 8 caracteres")
    full_name: Optional[str] = None


class AdminUpdateRequest(BaseModel):
    """Admin edita nome / email de outro admin (não muda role)."""
    full_name: Optional[str] = None
    email: Optional[str] = None  # re-mail exige unicidade


class AdminPasswordResetRequest(BaseModel):
    """Admin reseta senha de outro admin."""
    new_password: str = Field(..., min_length=8, description="Nova senha mínima 8 caracteres")
    reason: Optional[str] = None


@router.get("/admins", response_model=list[dict])
async def list_admins(
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os administradores do sistema (SUPER_ADMIN).
    Não inclui a si mesmo destacado de jeito nenhum — o admin pode ver quem mais é admin.
    """
    res = await db.execute(
        select(models.User)
        .where(models.User.role.in_(["admin", "SUPER_ADMIN"]))
        .order_by(models.User.created_at.desc())
    )
    admins = res.scalars().all()
    return [
        {
            "id": str(a.id),
            "email": a.email,
            "full_name": a.full_name,
            "role": a.role,
            "is_active": a.is_active,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "last_login_at": a.last_login_at.isoformat() if a.last_login_at else None,
            "is_self": a.id == admin.id,  # destaque visual no frontend
        }
        for a in admins
    ]


@router.post("/admins", status_code=201, response_model=dict)
async def create_admin(
    payload: AdminCreateRequest,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Cria novo administrador do sistema (SUPER_ADMIN).
    Admin criador não pode excluir a si mesmo, mas pode criar outros.
    """
    # Email único
    existing = await db.execute(
        select(models.User).where(func.lower(models.User.email) == payload.email.lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    new_admin = models.User(
        id=uuid.uuid4(),
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="SUPER_ADMIN",
        is_active=True,
        is_verified=True,
        onboarding_status="completed",
    )
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)

    logger.info(
        f"✅ Novo admin criado: {new_admin.email} (id={new_admin.id}) "
        f"por admin {admin.email}"
    )
    return {
        "id": str(new_admin.id),
        "email": new_admin.email,
        "full_name": new_admin.full_name,
        "role": new_admin.role,
        "is_active": new_admin.is_active,
        "created_at": new_admin.created_at.isoformat(),
    }


@router.put("/admins/{admin_id}", response_model=dict)
async def update_admin(
    admin_id: uuid.UUID,
    payload: AdminUpdateRequest,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Edita nome / email de um administrador (não muda role).
    Permite self-edit pra trocar email ou nome próprio.
    """
    res = await db.execute(
        select(models.User).where(models.User.id == admin_id)
    )
    target = res.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Administrador não encontrado")
    if target.role not in ("admin", "SUPER_ADMIN"):
        raise HTTPException(status_code=400, detail="Usuário não é administrador do sistema")

    # Valida unicidade de email se mudou
    if payload.email and payload.email.lower() != target.email.lower():
        existing = await db.execute(
            select(models.User).where(
                func.lower(models.User.email) == payload.email.lower(),
                models.User.id != admin_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email já em uso por outro usuário")
        target.email = payload.email

    if payload.full_name is not None:
        target.full_name = payload.full_name

    await db.commit()
    await db.refresh(target)

    logger.info(
        f"✅ Admin atualizado: {target.email} (id={target.id}) por admin {admin.email}"
    )
    return {
        "id": str(target.id),
        "email": target.email,
        "full_name": target.full_name,
        "role": target.role,
        "is_active": target.is_active,
    }


@router.delete("/admins/{admin_id}", status_code=204)
async def delete_admin(
    admin_id: uuid.UUID,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Remove um administrador do sistema.
    REGRAS DE SEGURANÇA:
    - Admin não pode remover a si mesmo
    - NÃO pode remover o último SUPER_ADMIN do sistema
    """
    if admin_id == admin.id:
        raise HTTPException(status_code=400, detail="Você não pode remover a si mesmo")

    res = await db.execute(
        select(models.User).where(models.User.id == admin_id)
    )
    target = res.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Administrador não encontrado")
    if target.role not in ("admin", "SUPER_ADMIN"):
        raise HTTPException(status_code=400, detail="Usuário não é administrador do sistema")

    # Conta quantos SUPER_ADMIN restam (excluindo o alvo)
    count_res = await db.execute(
        select(func.count(models.User.id)).where(
            models.User.role.in_(["admin", "SUPER_ADMIN"]),
            models.User.id != admin_id,
        )
    )
    remaining = count_res.scalar() or 0
    if remaining == 0:
        raise HTTPException(
            status_code=400,
            detail="Não é possível remover o último administrador do sistema. Crie outro antes."
        )

    await db.delete(target)
    await db.commit()

    logger.warning(
        f"⚠️ Admin removido: {target.email} (id={target.id}) por admin {admin.email}. "
        f"Restam {remaining} admin(s)."
    )
    return None


@router.post("/admins/{admin_id}/password", response_model=dict)
async def reset_admin_password(
    admin_id: uuid.UUID,
    payload: AdminPasswordResetRequest,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reseta a senha de outro admin (auditoria: loga quem mudou + motivo).
    Admin pode resetar própria senha também.
    """
    res = await db.execute(
        select(models.User).where(models.User.id == admin_id)
    )
    target = res.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Administrador não encontrado")
    if target.role not in ("admin", "SUPER_ADMIN"):
        raise HTTPException(status_code=400, detail="Usuário não é administrador do sistema")

    target.password_hash = hash_password(payload.new_password)
    await db.commit()

    logger.warning(
        f"🔐 Senha de admin resetada: {target.email} (id={target.id}) "
        f"por admin {admin.email}. Motivo: {payload.reason or 'não informado'}"
    )
    return {
        "id": str(target.id),
        "email": target.email,
        "message": "Senha atualizada com sucesso",
    }


# ============================================================
# 🆕 AUDIT LOG (admin only — investigar incidentes)
# ============================================================
@router.get("/audit/recent", response_model=list[dict])
async def list_recent_audit_logs(
    limit: int = 100,
    user_id: Optional[uuid.UUID] = None,
    action_filter: Optional[str] = None,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """🆕 Lista últimos audit_logs pra investigar incidentes.
    Filtros opcionais: user_id, action_filter (substring)."""
    from models import AuditLog

    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 500))
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action_filter:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action_filter}%"))

    res = await db.execute(stmt)
    logs = res.scalars().all()

    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            # 🆕 SECURITY: INET do Postgres vira IPv4Address, não serializa nativamente — converte pra str
            "ip_address": str(log.ip_address) if log.ip_address else None,
            "user_agent": (log.user_agent or "")[:200],
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ============================================================
# ATTRIBUTES
# ============================================================
@router.get("/attributes", response_model=list[schemas.AttributeDefinitionResponse])
async def list_attributes(
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lista definições de atributos"""
    res = await db.execute(
        select(models.AttributeDefinition)
        .where(models.AttributeDefinition.is_active == True)
        .order_by(models.AttributeDefinition.order_index)
    )
    return res.scalars().all()


@router.post("/attributes", response_model=schemas.AttributeDefinitionResponse, status_code=201)
async def create_attribute(
    payload: schemas.AttributeDefinitionCreate,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Cria novo atributo"""
    # Verifica code duplicado
    existing = await db.execute(
        select(models.AttributeDefinition).where(models.AttributeDefinition.code == payload.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Code já existe")

    attr = models.AttributeDefinition(
        id=uuid.uuid4(),
        code=payload.code,
        label=payload.label,
        description=payload.description,
        attribute_type=payload.attribute_type,
        options=payload.options,
        is_required=payload.is_required,
        is_onboarding=payload.is_onboarding,
        order_index=payload.order_index,
        validation_rules=payload.validation_rules,
        is_active=True,
    )
    db.add(attr)
    await db.commit()
    await db.refresh(attr)
    return attr


# ============================================================
# ONBOARDING CONFIG
# ============================================================
@router.get("/onboarding/config")
async def get_onboarding_config(
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retorna configuração de onboarding"""
    res = await db.execute(
        select(models.OnboardingConfig)
        .order_by(models.OnboardingConfig.step)
    )
    items = res.scalars().all()
    return [
        {
            "id": str(i.id),
            "step": i.step,
            "question_text": i.question_text,
            "helper_text": i.helper_text,
            "question_type": i.question_type,
            "attribute_code": i.attribute_code,
            "options": i.options,
            "is_active": i.is_active,
        }
        for i in items
    ]


@router.put("/onboarding/config")
async def update_onboarding_config(
    items: list[schemas.OnboardingConfigItem],
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Substitui configuração de onboarding (admin)"""
    # Remove existentes
    await db.execute(models.OnboardingConfig.__table__.delete())

    # Insere novos
    for item in items:
        config = models.OnboardingConfig(
            id=uuid.uuid4(),
            step=item.step,
            question_text=item.question_text,
            helper_text=item.helper_text,
            question_type=item.question_type,
            attribute_code=item.attribute_code,
            options=item.options,
            conditional_show=item.conditional_show,
            is_active=True,
        )
        db.add(config)

    await db.commit()
    return {"updated": len(items)}


# ============================================================
# KNOWLEDGE DOCUMENTS
# ============================================================
@router.get("/knowledge/list", response_model=list[schemas.KnowledgeDocumentResponse])
async def list_documents(
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lista documentos de conhecimento"""
    res = await db.execute(
        select(models.KnowledgeDocument).order_by(models.KnowledgeDocument.created_at.desc())
    )
    return res.scalars().all()


@router.post("/knowledge/upload", response_model=schemas.KnowledgeDocumentResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: str = Form(None),
    collection: str = Form("conhecimento_geral"),
    file: UploadFile = File(...),
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Upload de documento pra base de conhecimento"""
    # 🆕 SECURITY: valida tipo MIME (evita upload de binário arbitrário)
    ALLOWED_TYPES = {
        "application/pdf",
        "text/plain",
        "text/markdown",
        "text/x-markdown",
        "text/html",
    }
    if not file.content_type or file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de arquivo não permitido ({file.content_type}). Aceitos: PDF, TXT, MD, HTML."
        )

    # 🆕 SECURITY: limita tamanho (50MB)
    MAX_SIZE = 50 * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo muito grande ({len(file_bytes) // (1024*1024)}MB). Máximo: 50MB."
        )

    # Validação extra: filename não pode ter path traversal
    if file.filename and (".." in file.filename or "/" in file.filename or "\\" in file.filename):
        raise HTTPException(
            status_code=400,
            detail="Nome de arquivo inválido (não pode ter / ou ..)."
        )

    collection_folder = f"knowledge/{collection}" if collection else "knowledge"
    upload_result = await storage_service.upload(
        file_bytes=file_bytes,
        filename=file.filename,
        content_type=file.content_type,
        folder=collection_folder,
    )

    # Cria registro
    doc = models.KnowledgeDocument(
        id=uuid.uuid4(),
        title=title,
        description=description,
        file_name=file.filename,
        file_size_bytes=upload_result["size_bytes"],
        storage_url=upload_result["url"],
        storage_provider=upload_result["storage"],
        file_hash=upload_result.get("hash", ""),
        status="pending",
        chunks_count=0,
        uploaded_by=admin.id,
        collection=collection,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # REAL: dispara BackgroundTask pra chunking + embedding + Qdrant
    background_tasks.add_task(
        process_document_background,
        doc_id=str(doc.id),
        file_bytes=file_bytes,
        file_name=file.filename,
        collection=collection,
        db_url=str(db.bind.url) if db.bind else "",
    )

    logger.info(f"📚 Doc '{title}' salvo ({len(file_bytes)} bytes) - indexação em background")

    return doc


async def process_document_background(
    doc_id: str,
    file_bytes: bytes,
    file_name: str,
    collection: str,
    db_url: str,
):
    """Background: chunking + embedding + Qdrant"""
    from services.pdf_processor import pdf_processor
    from database import AsyncSessionLocal

    try:
        result = await pdf_processor.process_pdf(
            file_bytes=file_bytes,
            file_name=file_name,
            document_id=doc_id,
            collection=collection,
        )

        # Atualiza status no DB
        async with AsyncSessionLocal() as db:
            doc_res = await db.execute(
                select(models.KnowledgeDocument).where(models.KnowledgeDocument.id == uuid.UUID(doc_id))
            )
            doc = doc_res.scalar_one_or_none()
            if doc:
                if result.get("errors", 0) == 0 and result.get("indexed", 0) > 0:
                    doc.status = "indexed"
                    doc.chunks_count = result["indexed"]
                    doc.indexed_at = datetime.utcnow()
                else:
                    doc.status = "failed"
                    doc.error_message = f"{result.get('errors', 0)} erros no processamento"
                await db.commit()

        logger.info(f"✅ Background processado: doc {doc_id} status={doc.status if doc else 'unknown'}")
    except Exception as e:
        logger.error(f"❌ Erro no background processing: {e}", exc_info=True)
        # Marca como failed
        try:
            async with AsyncSessionLocal() as db:
                doc_res = await db.execute(
                    select(models.KnowledgeDocument).where(models.KnowledgeDocument.id == uuid.UUID(doc_id))
                )
                doc = doc_res.scalar_one_or_none()
                if doc:
                    doc.status = "failed"
                    doc.error_message = str(e)[:500]
                    await db.commit()
        except Exception:
            pass


@router.delete("/knowledge/{doc_id}", status_code=204)
async def delete_document(
    doc_id: uuid.UUID,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Deleta documento de conhecimento E TODOS os vestígios:
    1. Qdrant: TODOS os chunks indexados (conhecimento_geral)
    2. Azure Blob / Storage local: arquivo PDF original
    3. PostgreSQL: registro do documento

    Safety: rollback em caso de erro.
    """
    res = await db.execute(
        select(models.KnowledgeDocument).where(models.KnowledgeDocument.id == doc_id)
    )
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    deleted_summary = {"qdrant_chunks": 0, "storage": False}

    try:
        # 1. Qdrant: deleta chunks do documento (compilado/indexado)
        from services.vector_service import vector_service
        deleted_summary["qdrant_chunks"] = await vector_service.delete_document_chunks(str(doc_id))

        # 2. Storage (Azure Blob ou local): remove arquivo PDF original
        if doc.storage_url:
            # storage_service.delete() já extrai blob_path corretamente (incluindo pastas)
            storage_deleted = await storage_service.delete(doc.storage_url)
            deleted_summary["storage"] = storage_deleted

        # 3. PostgreSQL: deleta o registro
        await db.delete(doc)
        await db.commit()

        logger.info(
            f"✅ Documento '{doc.file_name}' ({doc_id}) excluído COMPLETAMENTE por admin {admin.email}. "
            f"Chunks Qdrant: {deleted_summary['qdrant_chunks']}, Storage: {deleted_summary['storage']}"
        )
        return None

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Erro ao excluir documento {doc_id}: {e}")
        # 🆕 SECURITY: mensagem genérica (não vaza str(e))
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao excluir documento. Tente novamente."
        )


# ============================================================
# OBSERVADOR - admin lê conversas/messages de OUTRO user (read-only)
# Cada acesso é registrado em audit_log (LGPD compliance)
# ============================================================
from routers.chats import list_chats as _user_list_chats
from routers.chats import list_messages as _user_list_messages
from utils.security import get_current_user
from sqlalchemy import desc


async def _log_admin_view(admin: models.User, target_user_id: str, action: str, details: dict, db: AsyncSession):
    """Helper: registra acesso de admin a dados de outro user (LGPD audit trail)."""
    from models import AuditLog  # importa no momento pra não carregar no startup
    entry = AuditLog(
        id=uuid.uuid4(),
        user_id=admin.id,
        action=action,
        resource_type="user",
        resource_id=uuid.UUID(target_user_id),
        details=details,
        ip_address=None,
        user_agent="ayria-admin-observer",
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    await db.commit()


@router.get("/users/{user_id}/chats", response_model=list[schemas.ChatResponse])
async def admin_list_user_chats(
    user_id: uuid.UUID,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin lista conversas de um user (MODO OBSERVADOR - read-only).

    Registra em audit_log: ação 'view_user_chats' com user_id do admin
    e resource_id do user observado.
    """
    # Verifica que o target existe
    target_res = await db.execute(select(models.User).where(models.User.id == user_id))
    target = target_res.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Busca chats do target
    res = await db.execute(
        select(models.Chat)
        .where(models.Chat.user_id == user_id, models.Chat.is_archived == False)
        .order_by(desc(models.Chat.last_message_at))
    )
    chats = res.scalars().all()

    result = []
    for chat in chats:
        count_res = await db.execute(
            select(func.count(models.Message.id)).where(models.Message.chat_id == chat.id)
        )
        count = count_res.scalar() or 0
        result.append(schemas.ChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            title=chat.title,
            summary=chat.summary,
            created_at=chat.created_at,
            last_message_at=chat.last_message_at,
            message_count=count,
        ))

    # Audit log (NÃO bloqueia se falhar - melhor logar de forma assíncrona)
    try:
        await _log_admin_view(
            admin=admin,
            target_user_id=str(user_id),
            action="view_user_chats",
            details={"chats_count": len(result), "target_email": target.email},
            db=db,
        )
    except Exception as e:
        logger.warning(f"Falha ao registrar audit log (view_user_chats): {e}")

    return result


@router.get("/users/{user_id}/chats/{chat_id}/messages", response_model=list[schemas.MessageResponse])
async def admin_list_user_chat_messages(
    user_id: uuid.UUID,
    chat_id: uuid.UUID,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin lista mensagens de um chat de um user (MODO OBSERVADOR - read-only).

    Verifica que o chat pertence ao user (anti-typo/anti-acesso-cruzado).
    Registra em audit_log: ação 'view_user_messages'.
    """
    # Verifica que o chat existe E pertence ao user
    chat_res = await db.execute(
        select(models.Chat).where(
            models.Chat.id == chat_id,
            models.Chat.user_id == user_id,
        )
    )
    chat = chat_res.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Conversa não encontrada para este usuário")

    # Busca mensagens
    res = await db.execute(
        select(models.Message)
        .where(models.Message.chat_id == chat_id)
        .order_by(models.Message.created_at)
    )
    messages = res.scalars().all()
    msgs = []
    for m in messages:
        # model_validate pega atributo `metadata` (MetaData do SQLAlchemy)
        # mas no model Message o atributo Python é `metadata_json` → pega manual
        msg_dict = {
            "id": m.id,
            "chat_id": m.chat_id,
            "user_id": m.user_id,
            "role": m.role,
            "content": m.content,
            "tokens_used": m.tokens_used,
            "ai_model": m.ai_model,
            "metadata": m.metadata_json or {},
            "created_at": m.created_at,
        }
        msgs.append(schemas.MessageResponse.model_validate(msg_dict))

    # Audit log
    try:
        await _log_admin_view(
            admin=admin,
            target_user_id=str(user_id),
            action="view_user_messages",
            details={"chat_id": str(chat_id), "messages_count": len(msgs), "chat_title": chat.title},
            db=db,
        )
    except Exception as e:
        logger.warning(f"Falha ao registrar audit log (view_user_messages): {e}")

    return msgs


# ============================================================
# PLANOS - admin pode editar (preço, créditos, ativo/inativo)
# ============================================================
@router.get("/plans", response_model=list[schemas.PlanResponse])
async def list_plans_admin(
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lista TODOS os planos (incluindo inativos)."""
    res = await db.execute(select(models.Plan).order_by(models.Plan.credits))
    return res.scalars().all()


@router.put("/plans/{plan_id}", response_model=schemas.PlanResponse)
async def update_plan(
    plan_id: uuid.UUID,
    payload: schemas.AdminPlanUpdate,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin edita um plano existente. NÃO permite mudar slug (identidade).

    IMPORTANTE: editar credits NÃO altera saldos de usuários existentes -
    só afeta novos cadastros. Para migrar usuários existentes, use
    /api/admin/credits/adjust ou troque o plano deles em /admin/users/{id}.
    """
    res = await db.execute(select(models.Plan).where(models.Plan.id == plan_id))
    plan = res.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    if payload.name is not None:
        plan.name = payload.name
    if payload.credits is not None:
        plan.credits = payload.credits
    if payload.price_brl is not None:
        plan.price_brl = payload.price_brl
    if payload.active is not None:
        plan.active = payload.active

    await db.commit()
    await db.refresh(plan)
    return plan


# ============================================================
# DETALHES COMPLETOS DE UM USUÁRIO (admin)
# ============================================================
@router.get("/users/{user_id}/details", response_model=schemas.AdminUserDetailResponse)
async def get_user_details(
    user_id: uuid.UUID,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retorna TUDO sobre um usuário: dados básicos, plano, créditos, perfil de onboarding,
    numerologia, astrologia, atributos dinâmicos, contagens de uso.

    Útil pro admin inspecionar o que cada user respondeu/gerou sem precisar de múltiplas chamadas.
    """
    # 1. User básico
    res = await db.execute(select(models.User).where(models.User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # 2. Plano selecionado
    plan = None
    if user.selected_plan_id:
        plan_res = await db.execute(select(models.Plan).where(models.Plan.id == user.selected_plan_id))
        plan = plan_res.scalar_one_or_none()

    # 3. Contagem de mensagens + chats
    msg_count_res = await db.execute(
        select(func.count(models.Message.id)).where(models.Message.user_id == user_id)
    )
    message_count = msg_count_res.scalar() or 0

    chats_count_res = await db.execute(
        select(func.count(models.Chat.id)).where(models.Chat.user_id == user_id)
    )
    chats_count = chats_count_res.scalar() or 0

    last_chat_res = await db.execute(
        select(func.max(models.Chat.updated_at)).where(models.Chat.user_id == user_id)
    )
    last_chat_at = last_chat_res.scalar()

    # 4. credit_transactions count
    tx_count_res = await db.execute(
        select(func.count(models.CreditTransaction.id)).where(models.CreditTransaction.user_id == user_id)
    )
    tx_count = tx_count_res.scalar() or 0

    # 5. profile_attributes (dados crus do onboarding - genero, data_nascimento, etc)
    profile_attrs = None
    prof_res = await db.execute(select(models.UserProfile).where(models.UserProfile.user_id == user_id))
    profile = prof_res.scalar_one_or_none()
    if profile:
        profile_attrs = profile.attributes  # jsonb direto

    # 6. Atributos dinâmicos (definidos em attribute_definitions, atribuídos via user_attributes)
    dynamic_attrs = []
    dyn_res = await db.execute(
        select(models.UserAttribute, models.AttributeDefinition)
        .join(models.AttributeDefinition, models.AttributeDefinition.id == models.UserAttribute.attribute_definition_id)
        .where(models.UserAttribute.user_id == user_id)
    )
    for ua, adef in dyn_res.all():
        dynamic_attrs.append(schemas.AdminUserAttributeValue(
            attribute_code=adef.code,
            attribute_name=adef.label,
            attribute_type=adef.attribute_type,
            value=ua.value,
        ))

    return schemas.AdminUserDetailResponse(
        # Básicos (herdado de AdminUserResponse)
        id=user.id, email=user.email, full_name=user.full_name, role=user.role,
        is_active=user.is_active, onboarding_status=user.onboarding_status or "pending",
        created_at=user.created_at, last_login_at=user.last_login_at,
        message_count=message_count,
        selected_plan_id=user.selected_plan_id,
        selected_plan_slug=plan.slug if plan else None,
        selected_plan_name=plan.name if plan else None,
        credit_balance=user.credit_balance or 0,
        credit_status=user.credit_status or "inactive",
        plan_selected_at=user.plan_selected_at,
        billing_status=user.billing_status or "billing_not_enabled",
        credits_last_granted_at=user.credits_last_granted_at,
        # Novos (específicos do detail)
        profile_attributes=profile_attrs,
        numerology_data=user.numerology_data,
        astrology_data=user.astrology_data,
        dynamic_attributes=dynamic_attrs,
        chats_count=chats_count,
        credit_transactions_count=tx_count,
        last_chat_at=last_chat_at,
        avatar_url=user.avatar_url,
        profile_status=user.profile_status,
    )


# ============================================================
# CONFIGURAÇÕES DO SISTEMA (apenas admin)
# ============================================================

@router.get("/config/ai", response_model=dict)
async def get_ai_config(admin=Depends(require_admin)):
    """Retorna config da IA em uso (provider, modelo, URL, status da chave).
    19/07/2026: Agora usa DB > .env (RuntimeConfig). Mostra source de cada campo.
    """
    from database import settings
    from services.ai_service import ai_service
    runtime = await ai_service.get_runtime_status()
    return {
        "ai": runtime,
        "embedding_provider": "MiniMax (ou hash fallback se MiniMax não suportar embeddings)",
        "azure_storage": {
            "configured": bool(storage_service.sas_url),
            "container": storage_service.container_name,
            "sas_expires": "2036-06-28 (10 anos)",  # até atualizar
            "use_local_fallback": storage_service.use_local,
        },
        "environment": settings.ENVIRONMENT,
        "rules": [
            "APENAS MiniMax (regra absoluta do sistema)",
            "OpenAI foi REMOVIDO COMPLETAMENTE",
            "Modelo padrão: MiniMax-M3",
            "Valores em verde no painel = vindos do DB (editáveis)",
        ],
    }


class AIConfigUpdate(BaseModel):
    """Update parcial da config de IA. Qualquer campo omitido mantém valor atual."""
    provider: Optional[str] = Field(default=None, description="Ex: 'MiniMax'")
    model: Optional[str] = Field(default=None, description="Ex: 'MiniMax-M3'")
    base_url: Optional[str] = Field(default=None, description="URL base OpenAI-compat")
    api_key: Optional[str] = Field(default=None, min_length=1, description="Chave de API (será persistida no DB)")
    reset_to_env: Optional[bool] = Field(default=False, description="Se True, limpa DB e volta pro .env")


@router.put("/config/ai", response_model=dict)
async def update_ai_config(
    payload: AIConfigUpdate,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Edita a config de IA em runtime (sobrescreve .env).
    Persistido no DB (tabela system_config). Aplicação imediata nas próximas requests.

    Validações:
    - API key: min 8 chars (validado na entrada)
    - Base URL: deve começar com http(s)://
    - Model: não vazio
    - reset_to_env=True: apaga todas as chaves AI_* do DB
    """
    from services.runtime_config import rc
    from services.ai_service import ai_service

    if payload.reset_to_env:
        # Limpa tudo do DB
        for k in ("AI_PROVIDER", "AI_MODEL", "AI_BASE_URL", "AI_API_KEY"):
            await rc.delete(db, k)
        runtime = await ai_service.get_runtime_status()
        return {
            "ok": True,
            "message": "Config resetada para o .env",
            "ai": runtime,
        }

    updates = []
    if payload.provider is not None:
        if not payload.provider.strip():
            raise HTTPException(status_code=400, detail="Provider não pode ser vazio")
        await rc.set(db, "AI_PROVIDER", payload.provider.strip(),
                     updated_by=admin.id,
                     description="Provider da IA (MiniMax)")
        updates.append("AI_PROVIDER")

    if payload.model is not None:
        if not payload.model.strip():
            raise HTTPException(status_code=400, detail="Model não pode ser vazio")
        await rc.set(db, "AI_MODEL", payload.model.strip(),
                     updated_by=admin.id,
                     description="Modelo da IA (ex: MiniMax-M3, MiniMax-M2.7)")
        updates.append("AI_MODEL")

    if payload.base_url is not None:
        if not payload.base_url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Base URL deve começar com http(s)://")
        await rc.set(db, "AI_BASE_URL", payload.base_url.strip(),
                     updated_by=admin.id,
                     description="URL base OpenAI-compat")
        updates.append("AI_BASE_URL")

    if payload.api_key is not None:
        if len(payload.api_key) < 8:
            raise HTTPException(status_code=400, detail="API key deve ter pelo menos 8 caracteres")
        await rc.set(db, "AI_API_KEY", payload.api_key,
                     updated_by=admin.id,
                     description="Chave de API da IA (NÃO compartilhar)")
        updates.append("AI_API_KEY")

    runtime = await ai_service.get_runtime_status()
    logger.warning(
        f"⚙️ AI config atualizada por admin {admin.email}: {updates}"
    )
    return {
        "ok": True,
        "message": f"Config atualizada: {', '.join(updates) if updates else 'nada'}",
        "updated": updates,
        "ai": runtime,
    }


@router.get("/config/system", response_model=dict)
async def get_system_config(admin=Depends(require_admin)):
    """Retorna status geral do sistema."""
    from database import settings
    from services.ai_service import ai_service
    return {
        "environment": settings.ENVIRONMENT,
        "ai": ai_service.get_status(),
        "azure": {
            "configured": bool(storage_service.sas_url),
            "container": storage_service.container_name,
            "use_local_fallback": storage_service.use_local,
        },
        "cors_origins": settings.CORS_ORIGINS.split(","),
        "jwt_expire_minutes": settings.JWT_EXPIRE_MINUTES,
    }


# ============================================================
# DEBUG: saúde detalhada do Qdrant (saber se DNS/rede estão OK)
# ============================================================
@router.get("/debug/qdrant", response_model=dict)
async def debug_qdrant(admin=Depends(require_admin)):
    """Diagnóstico do Qdrant: retorna URL efetiva, status, coleções, latência."""
    from database import settings
    import urllib.request, urllib.error, ssl, time as _time, socket

    url = settings.QDRANT_URL
    api_key_set = bool(settings.QDRANT_API_KEY)

    out = {
        "qdrant_url": url,
        "qdrant_api_key_set": api_key_set,
        "qdrant_api_key_preview": (settings.QDRANT_API_KEY[:8] + "...") if api_key_set else None,
        "reachable": False,
        "latency_ms": None,
        "collections": [],
        "error": None,
    }

    # Teste de reachability rápido (3s)
    try:
        start = _time.time()
        # /healthz é endpoint leve do Qdrant
        health_url = url.rstrip("/") + "/healthz"
        req = urllib.request.Request(health_url, method="GET")
        if api_key_set:
            req.add_header("api-key", settings.QDRANT_API_KEY)
        with urllib.request.urlopen(req, timeout=3) as resp:
            out["latency_ms"] = int((_time.time() - start) * 1000)
            out["healthz_body"] = resp.read()[:200].decode("utf-8", errors="replace")
        # Se respondeu, lista coleções
        collections_url = url.rstrip("/") + "/collections"
        req2 = urllib.request.Request(collections_url, method="GET")
        if api_key_set:
            req2.add_header("api-key", settings.QDRANT_API_KEY)
        with urllib.request.urlopen(req2, timeout=3) as resp2:
            data = json.loads(resp2.read())
            out["collections"] = [c["name"] for c in data.get("result", {}).get("collections", [])]
        out["reachable"] = True
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        # DNS lookup pode falhar — testar com socket
        try:
            host = url.split("://", 1)[-1].split(":", 1)[0]
            socket.gethostbyname(host)
        except Exception as dns_err:
            out["dns_error"] = f"{type(dns_err).__name__}: {str(dns_err)[:200]}"

    return out


# ============================================================
# ALMA — Arquitetura Cognitiva Modular (Constituição + Módulos)
# ============================================================
from services.prompt_selector import (
    AVAILABLE_MODULES,
    load_constitution as _load_constitution_default,
    load_modules as _load_module_content_default,
)


@router.get("/prompt/modules/available", response_model=dict)
async def list_available_modules(admin=Depends(require_admin)):
    """Lista módulos .md disponíveis no filesystem (ainda não editados)."""
    modulos_info = []
    for key in AVAILABLE_MODULES:
        # Lê preview do arquivo
        from pathlib import Path
        p = Path(__file__).parent.parent / "prompts" / f"prompt_{key}.md"
        preview = ""
        if p.exists():
            content = p.read_text(encoding="utf-8")
            preview = content[:200]
        modulos_info.append({
            "key": key,
            "default_preview": preview,
        })
    return {
        "available_modules": AVAILABLE_MODULES,
        "count": len(AVAILABLE_MODULES),
        "modules": modulos_info,
        "constitution_preview": _load_constitution_default()[:300] if _load_constitution_default() else "",
    }


@router.get("/prompt/system", response_model=dict)
async def get_prompt_system(
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retorna a constituição ativa + módulos ativos customizados."""
    # Constituição
    res = await db.execute(
        select(models.AyriaPromptConfig).where(
            models.AyriaPromptConfig.is_active == True,
            models.AyriaPromptConfig.key == "constituicao_base",
        )
    )
    cfg_constitution = res.scalar_one_or_none()

    # Módulos customizados
    res_mod = await db.execute(
        select(models.AyriaPromptConfig).where(
            models.AyriaPromptConfig.is_active == True,
            models.AyriaPromptConfig.key.like("modulo_%"),
        )
    )
    modulos_db = res_mod.scalars().all()

    return {
        "active": {
            "key": "constituicao_base",
            "content": cfg_constitution.content if cfg_constitution else _load_constitution_default(),
            "description": cfg_constitution.description if cfg_constitution else "Constituição padrão (hardcoded — fallback)",
            "updated_at": cfg_constitution.updated_at.isoformat() if cfg_constitution else None,
            "is_custom": cfg_constitution is not None,
        },
        "default_template": _load_constitution_default(),
        "modulos_customizados": [
            {
                "key": m.key,
                "short_key": m.key.replace("modulo_", "", 1),
                "content": m.content,
                "description": m.description,
                "updated_at": m.updated_at.isoformat(),
                "is_custom": True,
            }
            for m in modulos_db
        ],
        "available_modules": AVAILABLE_MODULES,
    }


@router.put("/prompt/system", response_model=dict)
async def update_prompt_system(
    payload: dict,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Salva constituição OU módulo.

    body:
    - key: 'constituicao_base' OU 'modulo_<nome>' (ex: 'modulo_numerologia')
    - content: str
    - description?: str
    """
    content = payload.get("content", "").strip()
    description = payload.get("description", "").strip() or None
    key = payload.get("key", "constituicao_base").strip()

    if not content:
        raise HTTPException(status_code=400, detail="content não pode ser vazio")

    # Validação por tipo
    if key == "constituicao_base":
        # Constituição: SEM placeholders (não é template, é texto puro)
        pass
    elif key.startswith("modulo_"):
        # Módulo: não tem placeholders, é texto puro também
        short = key.replace("modulo_", "", 1)
        # Aceita módulos novos (criação livre pelo admin) — só valida formato
        if not short.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(
                status_code=400,
                detail=f"Nome de módulo inválido: '{short}'. Use letras, números, underscore.",
            )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"key inválida. Use 'constituicao_base' ou 'modulo_<nome>'.",
        )

    # Desativa configs anteriores com mesma key
    from sqlalchemy import update as _upd
    await db.execute(
        _upd(models.AyriaPromptConfig)
        .where(models.AyriaPromptConfig.key == key, models.AyriaPromptConfig.is_active == True)
        .values(is_active=False)
    )

    # Cria nova config ativa
    new_cfg = models.AyriaPromptConfig(
        id=uuid.uuid4(),
        key=key,
        content=content,
        is_active=True,
        description=description,
        updated_by=admin.id,
    )
    db.add(new_cfg)
    await db.commit()
    await db.refresh(new_cfg)

    # Se for módulo novo, cria o .md no disco (caso ainda não exista)
    if key.startswith("modulo_"):
        from pathlib import Path
        from services.prompt_selector import PROMPTS_DIR
        md_path = PROMPTS_DIR / f"prompt_{key.replace('modulo_', '', 1)}.md"
        if not md_path.exists():
            md_path.write_text(content, encoding="utf-8")
            logger.info(f"📄 Novo módulo criado em disco: {md_path}")

    # Invalida cache
    try:
        from routers.chat import _invalidate_prompt_cache
        _invalidate_prompt_cache()
    except Exception:
        pass

    return {
        "ok": True,
        "id": str(new_cfg.id),
        "key": new_cfg.key,
        "is_active": new_cfg.is_active,
        "updated_at": new_cfg.updated_at.isoformat(),
    }


@router.post("/prompt/system/restore-default", response_model=dict)
async def restore_default_prompt(
    payload: dict | None = None,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Restaura padrão. Se payload.key fornecido, restaura só aquele; senão todos."""
    payload = payload or {}
    target_key = payload.get("key")

    from sqlalchemy import update as _upd

    if target_key:
        if target_key not in ["constituicao_base"] + [f"modulo_{m}" for m in AVAILABLE_MODULES]:
            raise HTTPException(status_code=400, detail=f"key inválida: {target_key}")
        res = await db.execute(
            _upd(models.AyriaPromptConfig)
            .where(models.AyriaPromptConfig.key == target_key, models.AyriaPromptConfig.is_active == True)
            .values(is_active=False)
        )
        msg = f"'{target_key}' restaurado pro padrão."
    else:
        res = await db.execute(
            _upd(models.AyriaPromptConfig).where(models.AyriaPromptConfig.is_active == True)
            .values(is_active=False)
        )
        msg = "Todos os prompts customizados desativados."

    # Invalida cache
    try:
        from routers.chat import _invalidate_prompt_cache
        _invalidate_prompt_cache()
    except Exception:
        pass

    return {
        "ok": True,
        "deactivated": res.rowcount or 0,
        "message": msg,
    }


# ============================================================
# DELETE — Remove módulo customizado (banco + arquivo + RAG)
# ============================================================
@router.delete("/prompt/module/{module_key:path}", response_model=dict)
async def delete_module(
    module_key: str,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove um módulo temático do sistema.

    - Constituição NÃO pode ser deletada (sempre existe)
    - Desativa registros do banco (soft delete histórico preservado)
    - Remove o arquivo .md se existir
    - Remove chunks do RAG (Qdrant)
    - Invalida cache

    path param: short_name (ex: 'numerologia', 'tarot')
    """
    import shutil
    from pathlib import Path
    from sqlalchemy import update as _upd

    full_key = f"modulo_{module_key}"

    # Validação do nome
    if not module_key.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail=f"Nome inválido: '{module_key}'. Use letras, números, underscore.",
        )

    file_path = PROMPTS_DIR / f"prompt_{module_key}.md"

    # 1. Desativa configs no banco (soft delete — preserva histórico)
    deactivated = 0
    try:
        res = await db.execute(
            _upd(models.AyriaPromptConfig)
            .where(models.AyriaPromptConfig.key == full_key, models.AyriaPromptConfig.is_active == True)
            .values(is_active=False)
        )
        deactivated = res.rowcount or 0
        await db.commit()
    except Exception as e:
        logger.warning(f"Erro ao desativar config: {e}")

    # 2. Apaga arquivo .md do disco
    file_removed = False
    backup_path = None
    if file_path.exists():
        # Backup de segurança antes de remover
        backup_path = file_path.with_suffix(file_path.suffix + ".deleted")
        try:
            shutil.copy2(file_path, backup_path)
            file_path.unlink()
            file_removed = True
            logger.info(f"🗑️ Módulo removido: {file_path}")
        except Exception as e:
            logger.error(f"Erro ao remover arquivo {file_path}: {e}")

    # 3. Remove do RAG (Qdrant)
    rag_deleted = False
    try:
        from services.prompt_indexer import delete_prompt_source
        await delete_prompt_source(f"prompt_{module_key}")
        rag_deleted = True
    except Exception as e:
        logger.warning(f"Erro ao remover do RAG: {e}")

    # 4. Remove de AVAILABLE_MODULES em memória
    if module_key in AVAILABLE_MODULES:
        AVAILABLE_MODULES.remove(module_key)

    # 5. Invalida cache do chat
    try:
        from routers.chat import _invalidate_prompt_cache
        _invalidate_prompt_cache()
    except Exception:
        pass

    # 6. Reindexa AVAILABLE_MODULES do filesystem (caso ainda tenha outros)
    try:
        AVAILABLE_MODULES.clear()
        AVAILABLE_MODULES.extend(sorted([
            p.stem.replace("prompt_", "")
            for p in PROMPTS_DIR.glob("prompt_*.md")
        ]))
        AVAILABLE_MODULES[:] = [m for m in AVAILABLE_MODULES if m != "base"]
    except Exception:
        pass

    return {
        "ok": True,
        "module_key": module_key,
        "full_key": full_key,
        "deactivated_configs": deactivated,
        "file_removed": file_removed,
        "backup_path": str(backup_path) if backup_path else None,
        "rag_cleared": rag_deleted,
        "available_modules_after": AVAILABLE_MODULES,
    }


# ============================================================
# RAG — Indexação dos .md de prompt no Qdrant
# ============================================================
@router.get("/prompt/rag/status", response_model=dict)
async def prompt_rag_status(admin=Depends(require_admin)):
    """Status da indexação RAG dos .md de prompt."""
    from services.prompt_indexer import list_indexed_prompts, PROMPTS_DIR
    from services.vector_service import VectorService

    files = sorted([f.name for f in PROMPTS_DIR.glob("*.md")])
    indexed = await list_indexed_prompts()
    indexed_sources = {d["source"] for d in indexed}

    return {
        "files_on_disk": files,
        "files_count": len(files),
        "indexed_count": len(indexed),
        "missing_index": [f for f in files if f.replace(".md", "") not in indexed_sources],
        "indexed_docs": indexed,
    }


@router.post("/prompt/rag/index", response_model=dict)
async def prompt_rag_index(
    payload: dict | None = None,
    admin=Depends(require_admin),
):
    """Indexa/reindexa os .md de prompt no Qdrant.

    body: { source?: str, recreate?: bool }
    - source: reindexa SÓ essa fonte (ex: 'prompt_numerologia'). Se vazio, indexa tudo.
    - recreate: se True, deleta docs antigos antes (default: True pra source específica, False pra all).
    """
    from services.prompt_indexer import index_all_prompts, delete_prompt_source, PROMPTS_DIR
    from services.pdf_processor import PDFProcessor
    from services.vector_service import VectorService

    payload = payload or {}
    source = payload.get("source")
    recreate = payload.get("recreate", bool(source))

    logger.info(f"🔄 Reindex RAG iniciado: source={source!r}, recreate={recreate}")

    try:
        if source:
            # Reindexar 1 arquivo específico
            from services.prompt_indexer import _index_single
            p = PROMPTS_DIR / f"{source}.md"
            if not p.exists():
                raise HTTPException(status_code=404, detail=f"Arquivo {source}.md não existe.")

            logger.info(f"  → Deletando source antiga: {source}")
            deleted = await delete_prompt_source(source)
            logger.info(f"  → Deleted: {deleted}")
            logger.info(f"  → Indexando: {p}")
            result = await _index_single(p)
            logger.info(f"  ✅ Source {source} reindexada: {result}")
            return {"ok": True, "source": source, "deleted": deleted, **result}

        # Indexar todos
        logger.info(f"  → Indexando TODOS os prompts (recreate={recreate})")
        result = await index_all_prompts(recreate=bool(recreate))
        logger.info(f"  ✅ Reindex completo: {result}")
        return {"ok": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Reindex RAG falhou: source={source!r}, recreate={recreate}")
        raise HTTPException(status_code=500, detail=f"Erro ao reindexar: {type(e).__name__}: {e}")


@router.post("/prompt/rag/delete", response_model=dict)
async def prompt_rag_delete(
    payload: dict,
    admin=Depends(require_admin),
):
    """Remove uma fonte do Qdrant (ex: 'prompt_numerologia')."""
    from services.prompt_indexer import delete_prompt_source

    source = payload.get("source", "").strip()
    if not source:
        raise HTTPException(status_code=400, detail="source obrigatório")

    deleted = await delete_prompt_source(source)
    return {"ok": True, "deleted": deleted, "source": source}


# ============================================================
# PROMPT CHAT — admin conversa COM contexto do MD carregado
# ============================================================
def _split_thinking_for_admin(content: str) -> tuple[str, str | None]:
    """
    Wrapper de routers.chat._split_thinking pra evitar duplicação.
    Sempre aplicado no chat de administração (config de MDs).
    """
    try:
        from routers.chat import _split_thinking
        return _split_thinking(content)
    except Exception:
        return content, None


class PromptChatRequest(BaseModel):
    """Mensagem do admin sobre um MD específico."""
    key: str  # ex: "constituicao_base", "modulo_numerologia", "supervisor_seguranca_crise", ou "modulo_<novo>"
    user_message: str
    history: Optional[list] = []  # [{"role":"user|assistant","content":"..."}]
    # Quando cria módulo NOVO: passa o rascunho inicial aqui (vai virar conteúdo "atual" pro contexto)
    initial_context: Optional[str] = None


class PromptChatSaveRequest(BaseModel):
    """Salva MD atualizado sugerido pelo chat."""
    key: str
    new_content: str
    reindex_rag: bool = True


@router.post("/prompt/chat", response_model=dict)
async def prompt_chat(
    payload: PromptChatRequest,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin conversa COM contexto de um MD específico.

    Carrega o conteúdo atual do MD e envia junto pro LLM, junto com a pergunta
    do admin. O LLM age como co-editor: identifica erros, sugere melhorias,
    propõe nova versão.

    Não altera nenhum arquivo — só retorna a sugestão. Quem salva é o botão
    "Salvar" do frontend, que chama /prompt/chat/save.
    """
    from services.ai_service import ai_service

    key = payload.key.strip()

    # 1. Carrega conteúdo atual do MD (banco > arquivo > initial_context do frontend pra módulos novos)
    current_content = None
    if payload.initial_context:
        # 🆕 Caso criação de módulo novo: usa o rascunho que o admin escreveu
        current_content = payload.initial_context
    if key == "constituicao_base":
        # Constituição: banco > arquivo .md
        res = await db.execute(
            select(models.AyriaPromptConfig).where(
                models.AyriaPromptConfig.key == "constituicao_base",
                models.AyriaPromptConfig.is_active == True,
            )
        )
        cfg = res.scalar_one_or_none()
        if cfg:
            current_content = cfg.content
        else:
            md_path = PROMPTS_DIR / "prompt_base.md"
            if md_path.exists():
                current_content = md_path.read_text(encoding="utf-8")
    elif key.startswith("modulo_"):
        short = key.replace("modulo_", "", 1)
        # Banco > arquivo
        res = await db.execute(
            select(models.AyriaPromptConfig).where(
                models.AyriaPromptConfig.key == key,
                models.AyriaPromptConfig.is_active == True,
            )
        )
        cfg = res.scalar_one_or_none()
        if cfg:
            current_content = cfg.content
        else:
            md_path = PROMPTS_DIR / f"prompt_{short}.md"
            if md_path.exists():
                current_content = md_path.read_text(encoding="utf-8")
    elif key == SUPERVISOR_PROMPT_KEY:
        # Supervisor: banco > arquivo
        res = await db.execute(
            select(models.AyriaPromptConfig).where(
                models.AyriaPromptConfig.key == SUPERVISOR_PROMPT_KEY,
                models.AyriaPromptConfig.is_active == True,
            )
        )
        cfg = res.scalar_one_or_none()
        if cfg:
            current_content = cfg.content
        else:
            if SUPERVISOR_PROMPT_FILE.exists():
                current_content = SUPERVISOR_PROMPT_FILE.read_text(encoding="utf-8")
    else:
        raise HTTPException(status_code=400, detail=f"key inválida: {key}")

    if not current_content:
        raise HTTPException(status_code=404, detail=f"Conteúdo não encontrado para '{key}'")

    # 2. Monta system prompt: você é editor do MD X
    # Injeta contexto cross-file pra IA enxergar a arquitetura toda
    from services.prompt_relationships import (
        build_architecture_map,
        get_summary_of_siblings,
    )

    architecture_map = build_architecture_map(key)
    sibling_summary = get_summary_of_siblings(key, max_chars=1500)

    system_prompt = f"""Você é o co-editor do Rafael (admin) sobre um prompt do sistema AYRIA.

**Contexto**: O admin está editando o arquivo/prompt de key `{key}`.

**Suas tarefas**:
- Pedir análise crítica do conteúdo
- Sugerir melhorias (clareza, cobertura, exemplos)
- Identificar erros, inconsistências ou lacunas
- Propor nova versão do texto (sempre em bloco markdown)
- Tirar dúvidas sobre o que o prompt faz

---

{architecture_map}

---

**Conteúdo ATUAL do prompt `{key}`**:
```markdown
{current_content}
```

---

{sibling_summary}

---

**Suas regras**:
1. SEMPRE responda em Português do Brasil (pt-BR).
2. Seja direto: prefira bullets e exemplos a textão.
3. 🎯 **QUANDO PROPOR VERSÃO NOVA**: você DEVE começar o bloco com 3 crases seguido de "markdown" (ex: ```\nmarkdown\nconteúdo aqui) na primeira linha, seguido do conteúdo completo do MD, e fechar com 3 crases. SEMPRE. Sem isso o botão Salvar não aparece.
   - Formato obrigatório: bloco com 3 crases (```) envolvendo o markdown completo
   - O bloco markdown deve vir **depois** de qualquer análise textual (separação clara)
4. Identifique problemas concretos: "linha X fala Y, mas Z contradiz" — seja específico.
5. ⚠️ SE detectar duplicação ou contradição com outro arquivo (ver mapa acima), AVISE no INÍCIO da resposta com ⚠️ e sugira onde colocar em vez de duplicar.
6. Sugira mudanças que melhorem o produto (não otimização acadêmica).
7. Se o admin só fizer uma pergunta conceitual, responda sem forçar nova versão.
8. Use o histórico da conversa pra não repetir contexto.
9. 🌐 NUNCA use caracteres de outros idiomas (chinês, japonês, coreano, árabe, cirílico).
10. 📝 Use a estrutura do MAPA acima pra decidir onde cada regra pertence (Constituição vs módulo vs supervisor).

**Padrão de resposta quando o admin pedir uma versão nova**:
```
[análise textual curta — opcional]

💡 **Posso salvar essa versão?** Se sim, é só clicar em **Salvar**.

```markdown
# MÓDULO: NOME
[conteúdo completo]
```

**Padrão de resposta quando detecta problema**:
```
⚠️ ATENÇÃO: [descrição do problema]. 

📋 Recomendação: [sugestão concreta — onde colocar, como ajustar]

💡 **Posso salvar essa versão?** Se sim, é só clicar em **Salvar**.

```markdown
[conteúdo completo corrigido]
```
```
"""

    # 3. Monta messages: history + user_message
    messages = [{"role": "system", "content": system_prompt}]
    for h in (payload.history or []):
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": payload.user_message})

    # 4. Chama LLM
    import time as _time
    _t0 = _time.time()
    logger.info(f"[prompt_chat:{key}] iniciando - {len(payload.user_message)} chars do user, contexto {len(current_content)} chars, {len(messages)} msgs no histórico")
    try:
        # Temperatura baixa (0.3) e mais tokens — escrita estruturada exige determinismo
        response = await ai_service.chat(
            messages=messages,
            temperature=0.3,
            max_tokens=4000,
        )
        _t1 = _time.time()
        logger.info(f"[prompt_chat:{key}] LLM respondeu em {_t1-_t0:.1f}s")
        ai_response = response.choices[0].message.content
        ai_model = response.model

        # 🧠 Suprime thinking vazado (mesma lógica do chat principal)
        ai_response, _ai_thinking = _split_thinking_for_admin(ai_response)
        if _ai_thinking:
            logger.info(f"[prompt_chat:{key}] AI vazou thinking ({len(_ai_thinking)} chars), suprimido.")

        # Sanitiza (mesma defesa anti-CJK do chat principal)
        from services.text_sanitizer import sanitize_response
        ai_response, _ = sanitize_response(ai_response, source=f"prompt_chat:{key}")
    except Exception as e:
        _t1 = _time.time()
        logger.exception(f"[prompt_chat:{key}] LLM falhou após {_t1-_t0:.1f}s: {type(e).__name__}: {e}")
        raise HTTPException(status_code=503, detail=f"Erro no LLM: {type(e).__name__}: {str(e)[:300]}")

    return {
        "ok": True,
        "key": key,
        "user_message": payload.user_message,
        "assistant_response": ai_response,
        "current_content_length": len(current_content),
        "model_used": ai_model,
    }


@router.post("/prompt/chat/save", response_model=dict)
async def prompt_chat_save(
    payload: PromptChatSaveRequest,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Salva nova versão do MD vinda do chat. Reusa a lógica de update_prompt_system
    mas adiciona:
    - Backup automático do arquivo atual (.md.bak)
    - Reindexação opcional no RAG
    - Validação mínima
    """
    import shutil
    from sqlalchemy import update as _upd

    key = payload.key.strip()
    new_content = payload.new_content.strip()

    if not new_content:
        raise HTTPException(status_code=400, detail="new_content vazio")
    if len(new_content) < 50:
        raise HTTPException(status_code=400, detail="new_content muito curto (mínimo 50 chars)")

    # Validação por tipo
    if key == "constituicao_base":
        file_path = PROMPTS_DIR / "prompt_base.md"
    elif key.startswith("modulo_"):
        short = key.replace("modulo_", "", 1)
        if not short.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(status_code=400, detail=f"Nome inválido: {short}")
        file_path = PROMPTS_DIR / f"prompt_{short}.md"
    elif key == SUPERVISOR_PROMPT_KEY:
        file_path = SUPERVISOR_PROMPT_FILE
    else:
        raise HTTPException(status_code=400, detail=f"key inválida: {key}")

    backup_path = None
    backup_warning = None
    if file_path.exists():
        backup_path = file_path.with_suffix(file_path.suffix + ".bak")
        try:
            shutil.copy2(file_path, backup_path)
        except (PermissionError, OSError) as e:
            # 🆕 22/07/2026 — Backup é best-effort: .bak antigo do root ou diretório read-only
            # NÃO pode bloquear save. Segue sem backup, mas avisa.
            backup_warning = f"{type(e).__name__}: {e}"
            backup_path = None
            logger.warning(f"[prompt_chat_save:{key}] Backup falhou (não-bloqueante): {backup_warning}")

    # Salva no banco (config ativa) + arquivo
    await db.execute(
        _upd(models.AyriaPromptConfig)
        .where(models.AyriaPromptConfig.key == key, models.AyriaPromptConfig.is_active == True)
        .values(is_active=False)
    )
    new_cfg = models.AyriaPromptConfig(
        id=uuid.uuid4(),
        key=key,
        content=new_content,
        is_active=True,
        description=f"Atualizado via chat pelo admin {admin.email}",
        updated_by=admin.id,
    )
    db.add(new_cfg)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(new_content, encoding="utf-8")

    await db.commit()
    await db.refresh(new_cfg)

    # Reindexa no RAG
    reindexed_chunks = 0
    if payload.reindex_rag and key != SUPERVISOR_PROMPT_KEY:
        try:
            from services.prompt_indexer import _index_single
            await _index_single(file_path)
            reindexed_chunks = -1  # sucesso (sem expor número exato)
        except Exception as e:
            logger.warning(f"Reindex RAG falhou pra {key}: {e}")

    # Invalida cache de prompt
    from routers.chat import _invalidate_prompt_cache
    _invalidate_prompt_cache()

    return {
        "ok": True,
        "key": key,
        "file": str(file_path),
        "backup": str(backup_path) if backup_path else None,
        "backup_warning": backup_warning,  # 🆕 22/07/2026 — best-effort backup
        "config_id": str(new_cfg.id),
        "reindexed": payload.reindex_rag,
        "content_length": len(new_content),
    }


# ============================================================
# SUPERVISOR PROMPT — módulo de SEGURANÇA E CRISE (separado!)
# ============================================================
SUPERVISOR_PROMPT_KEY = "supervisor_seguranca_crise"
SUPERVISOR_PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "supervisor" / "seguranca_crise.md"


@router.get("/supervisor/keywords", response_model=dict)
async def get_supervisor_keywords(
    admin: models.User = Depends(require_admin),
):
    """Retorna as keywords de crise parseadas do arquivo `keywords_crise.md`.

    Mostra na tela de Supervisão pra o admin ver exatamente o que está
    sendo matchado em cada nível. O arquivo é a fonte da verdade — reload
    é por mtime (sem restart).
    """
    from services.supervisor_service import SupervisorService

    # Carrega via o serviço (reusa o mtime/cache)
    raw = SupervisorService._load_keywords_from_md()
    # raw tem regex compiladas; pra exibir, decodificamos de volta o pattern.
    def serialize(patterns: list) -> list:
        out = []
        for p in patterns or []:
            try:
                txt = p.pattern.replace("\\b", "").replace("\\", "")
                out.append(txt)
            except Exception:
                continue
        return out

    categorias_def = [
        ("N1", "Risco imediato à vida (era: BLOQUEAVA chat)", "#EF4444"),
        ("N2", "Crimes / violência doméstica (era: BLOQUEAVA chat)", "#F59E0B"),
        ("N3", "Vícios / compulsões (era: NÃO bloqueia)", "#A855F7"),
        ("ATENCAO", "Sinais moderados (era: NÃO bloqueia)", "#FBBF24"),
        ("SLIGHT", "Verbos soltos — risco depende de contexto", "#94A3B8"),
        ("NEGATIVE", "Falsos positivos (anulam match de ATENCAO/SLIGHT)", "#6B7280"),
    ]

    payload = {
        "source": raw.get("_source"),
        "mtime": raw.get("_mtime"),
        "comportamento_atual": "NENHUMA categoria bloqueia o chat automaticamente. Admin decide via tela de Supervisão.",
        "categorias": [],
    }
    for key, label, color in categorias_def:
        patterns = serialize(raw.get(key, []))
        payload["categorias"].append({
            "key": key,
            "label": label,
            "color": color,
            "count": len(patterns),
            "patterns": patterns,
        })
    return payload


@router.get("/supervisor/keywords/source", response_model=dict)
async def get_supervisor_keywords_source(
    admin: models.User = Depends(require_admin),
):
    """Retorna o conteúdo CRU do arquivo `keywords_crise.md` (markdown original).

    Usado pelo editor frontend — a versão parseada (`/keywords`) é só pra visualização.
    """
    from services.supervisor_service import SupervisorService
    raw = SupervisorService._load_keywords_from_md()
    p = raw.get("_source")
    if not p:
        raise HTTPException(status_code=404, detail="keywords_crise.md não encontrado")
    from pathlib import Path
    pf = Path(p)
    if not pf.exists():
        raise HTTPException(status_code=404, detail="Arquivo inexistente")
    content = pf.read_text(encoding="utf-8")
    return {
        "source": str(pf),
        "content": content,
        "mtime": pf.stat().st_mtime,
        "size_bytes": len(content.encode("utf-8")),
    }


@router.put("/supervisor/keywords/source", response_model=dict)
async def update_supervisor_keywords_source(
    payload: dict,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # ⚠️ Capturar email cedo pra não ser afetado por expire_on_commit do SQLAlchemy
    admin_email = admin.email
    admin_id = admin.id
    """Salva o `keywords_crise.md` com backup automático.

    Validations:
    - content não vazio
    - precisa ter pelo menos 1 categoria N1/N2/N3
    - parse simples pra garantir que compila sem erro

    Backup: copia `.md` → `.md.bak.<timestamp>` antes de salvar.
    Audit log: action=keywords_update.
    """
    from services.supervisor_service import SupervisorService
    import shutil
    import time as _time
    from pathlib import Path

    content = (payload.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Conteúdo vazio")

    # Validação simples: precisa ter ## N1 (categorias)
    upper = content.upper()
    cats_found = sum(1 for c in ("## N1", "## N2", "## N3") if c in upper)
    if cats_found < 1:
        raise HTTPException(
            status_code=400,
            detail="Precisa ter pelo menos uma categoria N1/N2/N3 (linha começando com ## Nx)",
        )

    # Validação simples: tem pelo menos 1 keyword (linha começando com "- ")
    keywords_count = sum(1 for line in content.splitlines() if line.strip().startswith("-"))
    if keywords_count < 1:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma keyword encontrada (precisa de linhas começando com `- `)",
        )

    raw = SupervisorService._load_keywords_from_md()
    target = Path(raw.get("_source"))
    if not target.exists():
        raise HTTPException(status_code=404, detail="Arquivo original não existe")

    # Faz backup com timestamp (mantém últimos 10)
    backup_dir = target.parent / ".keywords_backups"
    backup_dir.mkdir(exist_ok=True)
    backup_name = f"keywords_crise.md.bak.{int(_time.time())}"
    backup_path = backup_dir / backup_name
    shutil.copy2(target, backup_path)
    # Limpa backups antigos (>10)
    backups = sorted(backup_dir.glob("keywords_crise.md.bak.*"))
    for old in backups[:-10]:
        try:
            old.unlink()
        except Exception:
            pass

    # Salva novo conteúdo
    target.write_text(content, encoding="utf-8")
    new_mtime = target.stat().st_mtime

    # Força reload no cache do service (chamando novamente invalida por mtime)
    SupervisorService._keywords_cache = None
    SupervisorService._keywords_mtime = 0
    SupervisorService._load_keywords_from_md()  # recarrega

    # Audit log
    try:
        from sqlalchemy import text as sql_text
        log_sql = sql_text("""
            INSERT INTO audit_log (id, actor_id, action, resource_type, resource_id, details, ip_address, user_agent, created_at)
            VALUES (gen_random_uuid(), :actor_id, 'keywords_update', 'supervisor_config', NULL,
                    CAST(:details AS JSONB), :ip, :ua, NOW())
        """)
        from utils.security import get_client_ip, get_user_agent
        await db.execute(
            log_sql,
            {
                "actor_id": admin_id,
                "details": json.dumps({"size_bytes": len(content.encode("utf-8")), "backup": str(backup_path)}),
                "ip": get_client_ip(request),
                "ua": get_user_agent(request),
            },
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"audit log falhou: {e}")
        try:
            await db.rollback()
        except Exception:
            pass

    logger.info(f"📝 keywords_crise.md atualizado por admin={admin_email} backup={backup_path}")

    return {
        "ok": True,
        "source": str(target),
        "mtime": new_mtime,
        "size_bytes": len(content.encode("utf-8")),
        "backup": str(backup_path),
        "keywords_count": content.count("\n- "),
    }


@router.post("/supervisor/keywords/restore-default", response_model=dict)
async def restore_default_keywords(
    request: Request,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    admin_email = admin.email
    admin_id = admin.id
    """Restaura o `keywords_crise.md` a partir do template hardcoded no código.

    O template padrão fica em `BACKEND_DEFAULT_KEYWORDS` neste arquivo.
    Backup do atual antes.
    """
    import shutil
    import time as _time
    from pathlib import Path

    DEFAULT_CONTENT = '''# KEYWORDS DE CRISE — AYRIA

Arquivo editável pelo admin. Cada linha = 1 keyword/frase regex.
O supervisor (sync + batch) usa estas keywords pra filtrar o que vai
ser analisado pela IA. Mensagens sem match são marcadas como NORMAL
**sem gastar chamada IA**.

## N1 — RISCO IMEDIATO À VIDA (CRÍTICO)
- "quero morrer"
- "vou me matar"
- "vou me suicidar"
- "tirar minha vida"
- "tirar a vida"
- "me matar"
- "vou sumir"
- "vou desaparecer"
- "não vou estar mais aqui"
- "não vou viver mais"
- "acabar com tudo"
- "me machucar"
- "me cortar"
- "me sangrar"
- "explodir tudo"
- "explodir a casa"
- "explodir a vida"
- "vou me explodir"
- "plano de morte"
- "plano de suicídio"
- "plano de me matar"
- "seria melhor se eu não existisse"
- "vou matar alguém"
- "vou matar ele"
- "vou matar ela"
- "estou pensando em matar"
- "vou fazer ele sofrer"
- "vou fazer ela sofrer"

## N2 — CRIMES / VIOLÊNCIA DOMÉSTICA (CRÍTICO)
- "vou roubar"
- "vou traficar"
- "vou agredir"
- "vou estuprar"
- "violência doméstica"
- "meu parceiro me bate"
- "minha parceira me bate"
- "meu marido me bate"
- "minha esposa me bate"
- "vou denunciar falso"
- "vou denunciar falsamente"
- "confesso que matei"
- "confesso que roubei"
- "confesso que agredi"
- "vou me vingar"
- "vou fazer justiça com as próprias mãos"

## N3 — VÍCIOS / COMPULSÕES (ATENÇÃO)
- "vício em apostas"
- "vício em jogo"
- "vício em cassino"
- "vício em bingo"
- "jogatina"
- "transtorno alimentar"
- "anorexia"
- "bulimia"
- "overdose"
- "overdosei"
- "álcool demais"
- "álcool em excesso"
- "drogas demais"
- "drogas em excesso"

## ATENCAO — SINAIS MODERADOS (batch + IA confirma)
Sinais de sofrimento emocional persistente. NÃO bloqueiam chat imediatamente,
mas o supervisor batch RODA IA pra confirmar/avaliar.

- "não aguento mais"
- "não suporto mais"
- "desespero"
- "sem saída"
- "sem esperança"
- "não tenho motivos"
- "ninguém se importa"
- "ninguém se importa comigo"
- "sou um fardo"
- "não sou bom o suficiente"
- "fracasso"
- "inútil"
- "deprimi"
- "deprimido"
- "deprimida"
- "ansiedade forte"
- "crise de ansiedade"
- "crise de pânico"
- "ataque de pânico"
- "chorando muito"
- "choro toda noite"
- "não consigo dormir"
- "insônia"
- "não consigo mais"
- "tô sozinho"
- "tô sozinha"
- "tô sozinho no mundo"
- "me sinto sozinho"
- "me sinto sozinha"
- "solidão"
- "abandono"
- "rejeitado"
- "rejeitada"
- "culpa"
- "me sinto culpado"
- "me sinto culpada"
- "arrependido"
- "arrependida"
- "por quê eu"
- "porque eu"

## COMO EDITAR
- Adicione novas keywords/frases regex em qualquer nível.
- N1/N2 = alerta URGÊNCIA (admin decide se bloqueia pelo painel).
- N3 e ATENCAO = alerta ATENÇÃO.
- Linhas começando com `#` são comentários.
'''

    from services.supervisor_service import SupervisorService
    raw = SupervisorService._load_keywords_from_md()
    target = Path(raw.get("_source"))

    backup_dir = target.parent / ".keywords_backups"
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / f"keywords_crise.md.bak.{int(_time.time())}"
    shutil.copy2(target, backup_path)

    target.write_text(DEFAULT_CONTENT, encoding="utf-8")

    # Força reload
    SupervisorService._keywords_cache = None
    SupervisorService._keywords_mtime = 0
    SupervisorService._load_keywords_from_md()

    # Audit
    try:
        from sqlalchemy import text as sql_text
        from utils.security import get_client_ip, get_user_agent
        log_sql = sql_text("""
            INSERT INTO audit_log (id, actor_id, action, resource_type, resource_id, details, ip_address, user_agent, created_at)
            VALUES (gen_random_uuid(), :actor_id, 'keywords_restore_default', 'supervisor_config', NULL,
                    CAST(:details AS JSONB), :ip, :ua, NOW())
        """)
        await db.execute(
            log_sql,
            {
                "actor_id": admin_id,
                "details": json.dumps({"size_bytes": len(DEFAULT_CONTENT.encode("utf-8")), "backup": str(backup_path)}),
                "ip": get_client_ip(request),
                "ua": get_user_agent(request),
            },
        )
        await db.commit()
    except Exception:
        await db.rollback()

    return {
        "ok": True,
        "restored": True,
        "source": str(target),
        "size_bytes": len(DEFAULT_CONTENT.encode("utf-8")),
        "backup": str(backup_path),
    }


@router.get("/supervisor/prompt", response_model=dict)
async def get_supervisor_prompt(
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retorna o prompt de segurança/crise (do banco OU do arquivo).

    O banco tem prioridade (customização do admin).
    O arquivo .md em prompts/supervisor/ é o fallback hardcoded.
    """
    # Tentar banco
    res = await db.execute(
        select(models.AyriaPromptConfig).where(
            models.AyriaPromptConfig.is_active == True,
            models.AyriaPromptConfig.key == SUPERVISOR_PROMPT_KEY,
        )
    )
    cfg = res.scalar_one_or_none()

    default_content = ""
    if SUPERVISOR_PROMPT_FILE.exists():
        default_content = SUPERVISOR_PROMPT_FILE.read_text(encoding="utf-8")

    return {
        "active": {
            "key": SUPERVISOR_PROMPT_KEY,
            "content": cfg.content if cfg else default_content,
            "description": cfg.description if cfg else "Padrão (arquivo supervisor/seguranca_crise.md)",
            "updated_at": cfg.updated_at.isoformat() if cfg else None,
            "is_custom": cfg is not None,
        },
        "default_content": default_content,
        "file_path": str(SUPERVISOR_PROMPT_FILE),
    }


@router.put("/supervisor/prompt", response_model=dict)
async def update_supervisor_prompt(
    payload: dict,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Edita o prompt do supervisor (NÃO bloqueia Ayria, só orienta o módulo).

    body: { content: str, description?: str }
    """
    content = payload.get("content", "").strip()
    description = payload.get("description", "").strip() or None

    if not content:
        raise HTTPException(status_code=400, detail="content não pode ser vazio")

    # Desativa versões anteriores
    from sqlalchemy import update as _upd
    await db.execute(
        _upd(models.AyriaPromptConfig)
        .where(
            models.AyriaPromptConfig.key == SUPERVISOR_PROMPT_KEY,
            models.AyriaPromptConfig.is_active == True,
        )
        .values(is_active=False)
    )

    new_cfg = models.AyriaPromptConfig(
        id=uuid.uuid4(),
        key=SUPERVISOR_PROMPT_KEY,
        content=content,
        is_active=True,
        description=description,
        updated_by=admin.id,
    )
    db.add(new_cfg)
    await db.commit()
    await db.refresh(new_cfg)

    # Invalida cache do chat
    try:
        from routers.chat import _invalidate_prompt_cache
        _invalidate_prompt_cache()
    except Exception:
        pass

    return {
        "ok": True,
        "id": str(new_cfg.id),
        "key": new_cfg.key,
        "is_active": new_cfg.is_active,
        "updated_at": new_cfg.updated_at.isoformat(),
    }


@router.post("/supervisor/prompt/restore-default", response_model=dict)
async def restore_supervisor_prompt_default(
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Restaura o prompt de supervisor pro padrão (arquivo .md)."""
    from sqlalchemy import update as _upd
    res = await db.execute(
        _upd(models.AyriaPromptConfig)
        .where(
            models.AyriaPromptConfig.key == SUPERVISOR_PROMPT_KEY,
            models.AyriaPromptConfig.is_active == True,
        )
        .values(is_active=False)
    )

    try:
        from routers.chat import _invalidate_prompt_cache
        _invalidate_prompt_cache()
    except Exception:
        pass

    return {
        "ok": True,
        "deactivated": res.rowcount or 0,
        "message": "Prompt do supervisor restaurado pro padrão.",
    }


# ============================================================
# 🆕 DB MAINTENANCE (19/07/2026)
# Botões que admin dispara pela aba "Manutenção":
# - GET   /api/admin/db/status         — stats em tempo real
# - POST  /api/admin/db/backup         — roda backup script
# - POST  /api/admin/db/vacuum         — vacuum + analyze + reindex
# - POST  /api/admin/db/trim-audit     — trim audit_log antigo
# - GET   /api/admin/db/backups        — lista backups existentes
# - POST  /api/admin/db/restore        — restaura de um backup (dry_run opcional)
# ============================================================
import subprocess as _sp
import os as _os

BACKUP_DIR = "/home/peron/backups/ayria-db"


@router.get("/db/status")
async def db_status(admin: models.User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """Status do banco em tempo real + último backup."""
    from database import settings as _s
    import json as _json
    from datetime import datetime as _dt

    # Stats gerais
    size = (await db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))"))).scalar()
    n_conn = (await db.execute(text("SELECT count(*) FROM pg_stat_activity"))).scalar() or 0

    # Top 5 maiores tabelas
    rows = (await db.execute(text("""
        SELECT
            t.schemaname || '.' || t.tablename AS tabela,
            pg_size_pretty(pg_total_relation_size(t.schemaname || '.' || t.tablename)) AS tamanho,
            pg_total_relation_size(t.schemaname || '.' || t.tablename) AS bytes,
            s.n_live_tup AS linhas,
            s.n_dead_tup AS mortas
        FROM pg_tables t
        JOIN pg_stat_user_tables s
          ON s.schemaname = t.schemaname AND s.relname = t.tablename
        WHERE t.schemaname = 'public'
        ORDER BY pg_total_relation_size(t.schemaname || '.' || t.tablename) DESC
        LIMIT 10
    """))).all()

    tables = [
        {"tabela": r[0], "tamanho": r[1], "bytes": r[2], "linhas": r[3], "mortas": r[4]}
        for r in rows
    ]

    # Último backup
    last_pg = None
    last_qdrant = None
    if _os.path.isdir(BACKUP_DIR):
        pg_files = sorted(_os.listdir(BACKUP_DIR)) if _os.path.exists(BACKUP_DIR) else []
        pg_bks = sorted([f for f in pg_files if f.startswith("pg_")])
        q_bks = sorted([f for f in pg_files if f.startswith("qdrant_")])
        if pg_bks:
            last_pg = {
                "file": pg_bks[-1],
                "size": _os.path.getsize(f"{BACKUP_DIR}/{pg_bks[-1]}"),
                "modified": _dt.fromtimestamp(_os.path.getmtime(f"{BACKUP_DIR}/{pg_bks[-1]}")).isoformat(),
            }
        if q_bks:
            last_qdrant = {
                "file": q_bks[-1],
                "size": _os.path.getsize(f"{BACKUP_DIR}/{q_bks[-1]}"),
                "modified": _dt.fromtimestamp(_os.path.getmtime(f"{BACKUP_DIR}/{q_bks[-1]}")).isoformat(),
            }

    return {
        "database": "ayria",
        "size": size,
        "active_connections": n_conn,
        "tables": tables,
        "backups": {
            "dir": BACKUP_DIR,
            "last_pg": last_pg,
            "last_qdrant": last_qdrant,
        },
        "environment": _s.ENVIRONMENT,
    }


@router.post("/db/backup")
async def db_backup(admin: models.User = Depends(require_admin)):
    """Roda backup local + ZIP + upload Azure (igual /backup-cloud). 19/07/2026."""
    from datetime import datetime as _dt
    import zipfile as _zip

    script = "/home/peron/bin/ayria-db-backup.sh"
    if not _os.path.isfile(script):
        raise HTTPException(404, f"Script não encontrado: {script}")

    # 1. Roda backup local
    try:
        result = _sp.run(["bash", script], capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return {
                "ok": False,
                "returncode": result.returncode,
                "stdout": result.stdout[-3000:],
                "stderr": result.stderr[-1000:] if result.stderr else "",
                "cloud_ok": False,
            }
    except _sp.TimeoutExpired:
        raise HTTPException(500, "Backup local demorou mais que 5min (timeout)")

    # 2. ZIP + upload Azure
    pg_files = sorted([f for f in _os.listdir(BACKUP_DIR) if f.startswith("pg_")])
    qdrant_files = sorted([f for f in _os.listdir(BACKUP_DIR) if f.startswith("qdrant_")])
    cloud_ok = False
    cloud_url = None
    cloud_path = None
    zip_size = 0
    zip_filename = None
    if pg_files:
        latest_pg = pg_files[-1]
        # extrai timestamp do pg_20260719_HHMMSS.sql.gz pra usar no zip
        import re as _re
        _m = _re.search(r"pg_(\d{8}_\d{6})", latest_pg)
        zip_ts = _m.group(1) if _m else _dt.now().strftime("%Y%m%d_%H%M%S")
        files_to_zip = [f"{BACKUP_DIR}/{latest_pg}"]
        if qdrant_files:
            files_to_zip.append(f"{BACKUP_DIR}/{qdrant_files[-1]}")
        zip_filename = f"ayria-backup-{zip_ts}.zip"
        tmp_zip = f"/tmp/{zip_filename}"
        with _zip.ZipFile(tmp_zip, "w", _zip.ZIP_DEFLATED, compresslevel=6) as zf:
            for fpath in files_to_zip:
                zf.write(fpath, arcname=_os.path.basename(fpath))
        zip_size = _os.path.getsize(tmp_zip)
        try:
            from services.storage_service import storage_service as _ss
            with open(tmp_zip, "rb") as f:
                file_bytes = f.read()
            upload_result = await _ss.upload(
                file_bytes=file_bytes,
                filename=zip_filename,
                content_type="application/zip",
                folder="backups",
            )
            cloud_ok = upload_result.get("storage") == "azure"
            cloud_url = upload_result.get("url")
            cloud_path = upload_result.get("path")
        except Exception as e:
            logger.error(f"❌ Upload Azure falhou (backup ainda tá local): {e}")
        try:
            _os.remove(tmp_zip)
        except Exception:
            pass

    # 3. Cleanup Azure >30 dias
    cleanup = {"deleted": 0}
    if cloud_ok:
        try:
            from services.storage_service import storage_service as _ss
            from datetime import timedelta as _td
            container = _ss._azure_container
            if container:
                cutoff = _dt.utcnow() - _td(days=30)
                for b in container.list_blobs(name_starts_with="backups/"):
                    if b.last_modified and b.last_modified.replace(tzinfo=None) < cutoff:
                        container.delete_blob(b.name)
                        cleanup["deleted"] += 1
        except Exception as e:
            logger.warning(f"⚠️ Cleanup Azure falhou: {e}")

    logger.warning(
        f"📦 Backup disparado por admin {admin.email}: "
        f"local+azure, zip={zip_size}B, cloud_ok={cloud_ok}, cleanup_deleted={cleanup['deleted']}"
    )

    return {
        "ok": True,
        "returncode": 0,
        "stdout": result.stdout[-3000:],
        "stderr": "",
        "zip_filename": zip_filename,
        "zip_size_bytes": zip_size,
        "cloud_ok": cloud_ok,
        "cloud_url": cloud_url,
        "cloud_path": cloud_path,
        "cleanup_deleted": cleanup["deleted"],
        "retention_days": 30,
    }



@router.post("/db/backup-cloud")
async def db_backup_cloud(admin: models.User = Depends(require_admin)):
    """Backup local + zip + upload pro Azure Blob (folder backups/). Limpa Azure >30 dias. (19/07/2026)"""
    from datetime import datetime as _dt
    import zipfile
    import tempfile as _tmp

    script = "/home/peron/bin/ayria-db-backup.sh"
    if not _os.path.isfile(script):
        raise HTTPException(404, f"Script não encontrado: {script}")

    # 1. Roda backup local
    try:
        result = _sp.run(["bash", script], capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise HTTPException(500, f"Backup local falhou: {result.stderr[:500]}")
    except _sp.TimeoutExpired:
        raise HTTPException(500, "Backup local demorou mais que 5min (timeout)")

    # 2. Pega arquivos gerados (pg_*.sql.gz + qdrant_*.tar.gz)
    pg_files = sorted([f for f in _os.listdir(BACKUP_DIR) if f.startswith("pg_")])
    qdrant_files = sorted([f for f in _os.listdir(BACKUP_DIR) if f.startswith("qdrant_")])
    if not pg_files:
        raise HTTPException(500, "Nenhum backup local gerado")
    latest_pg = pg_files[-1]
    files_to_zip = [f"{BACKUP_DIR}/{latest_pg}"]
    if qdrant_files:
        files_to_zip.append(f"{BACKUP_DIR}/{qdrant_files[-1]}")

    # 3. Zip tudo
    import re as _re2
    _m2 = _re2.search(r"pg_(\d{8}_\d{6})", latest_pg)
    zip_ts = _m2.group(1) if _m2 else _dt.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"ayria-backup-{zip_ts}.zip"
    tmp_zip = f"/tmp/{zip_filename}"
    with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for fpath in files_to_zip:
            zf.write(fpath, arcname=_os.path.basename(fpath))
    zip_size = _os.path.getsize(tmp_zip)

    # 4. Upload pro Azure
    from services.storage_service import storage_service
    try:
        with open(tmp_zip, "rb") as f:
            file_bytes = f.read()
        upload_result = await storage_service.upload(
            file_bytes=file_bytes,
            filename=zip_filename,
            content_type="application/zip",
            folder="backups",
        )
        cloud_ok = upload_result.get("storage") == "azure"
        cloud_url = upload_result.get("url")
        cloud_path = upload_result.get("path")
    except Exception as e:
        logger.error(f"❌ Upload Azure falhou: {e}")
        cloud_ok = False
        cloud_url = None
        cloud_path = None

    # 5. Apagar ZIP temporário
    try:
        _os.remove(tmp_zip)
    except Exception:
        pass

    # 6. Limpar Azure blobs >30 dias (cleanup retention)
    cleanup = {"deleted": 0, "errors": 0}
    if cloud_ok:
        try:
            from services.storage_service import storage_service as _ss
            container = _ss._azure_container
            if container:
                from datetime import timedelta as _td
                cutoff = _dt.utcnow() - _td(days=30)
                blobs = container.list_blobs(name_starts_with="backups/")
                for b in blobs:
                    try:
                        if b.last_modified and b.last_modified.replace(tzinfo=None) < cutoff:
                            container.delete_blob(b.name)
                            cleanup["deleted"] += 1
                    except Exception:
                        cleanup["errors"] += 1
        except Exception as e:
            logger.warning(f"⚠️ Cleanup Azure falhou: {e}")

    logger.warning(
        f"📦 Backup+Azure disparado por admin {admin.email}: "
        f"local_files={len(files_to_zip)}, zip={zip_size}B, "
        f"cloud_ok={cloud_ok}, deleted_old={cleanup['deleted']}"
    )

    return {
        "ok": True,
        "local_files": len(files_to_zip),
        "local_files_list": [_os.path.basename(f) for f in files_to_zip],
        "zip_filename": zip_filename,
        "zip_size_bytes": zip_size,
        "cloud_ok": cloud_ok,
        "cloud_url": cloud_url,
        "cloud_path": cloud_path,
        "cleanup_deleted": cleanup["deleted"],
        "cleanup_errors": cleanup["errors"],
        "retention_days": 30,
    }



@router.post("/db/vacuum")
async def db_vacuum(admin: models.User = Depends(require_admin)):
    """Roda VACUUM ANALYZE + REINDEX (mesmo do maintenance semanal)."""
    script = "/home/peron/bin/ayria-db-maintenance.sh"
    if not _os.path.isfile(script):
        raise HTTPException(404, f"Script não encontrado: {script}")

    try:
        result = _sp.run(
            ["bash", script, "--audit-keep", "180"],
            capture_output=True, text=True, timeout=900,  # 15min
        )
        logger.warning(f"🧹 Vacuum manual disparado por admin {admin.email}")
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-3000:],
            "stderr": result.stderr[-1000:] if result.stderr else "",
        }
    except _sp.TimeoutExpired:
        raise HTTPException(500, "Vacuum demorou mais que 15min (timeout)")
    except Exception as e:
        raise HTTPException(500, f"Erro ao rodar vacuum: {e}")


@router.post("/db/trim-audit")
async def db_trim_audit(
    payload: dict,
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Trim audit_log manual. payload = {days: int}"""
    days = int(payload.get("days", 180))
    if days < 30:
        raise HTTPException(400, "Mínimo 30 dias (segurança)")

    res = await db.execute(
        text(f"DELETE FROM audit_log WHERE created_at < NOW() - INTERVAL '{days} days' RETURNING id")
    )
    deleted = len(res.all())
    await db.commit()
    logger.warning(
        f"🗑️ Audit trim manual: {deleted} registros removidos (>{days} dias) por admin {admin.email}"
    )
    return {"ok": True, "deleted": deleted, "days": days}


@router.get("/db/backups")
async def db_backups_list(admin: models.User = Depends(require_admin)):
    """Lista backups LOCAIS + AZURE (com status e URL). 19/07/2026."""
    from datetime import datetime as _dt

    # 1. Listar arquivos locais
    files = []
    if _os.path.isdir(BACKUP_DIR):
        for fname in sorted(_os.listdir(BACKUP_DIR)):
            fpath = f"{BACKUP_DIR}/{fname}"
            if not _os.path.isfile(fpath) or fname.endswith(".log"):
                continue
            stat = _os.stat(fpath)
            files.append({
                "file": fname,
                "size": stat.st_size,
                "size_human": f"{stat.st_size / 1024:.1f} KB" if stat.st_size < 1024*1024 else f"{stat.st_size / 1024 / 1024:.2f} MB",
                "modified": _dt.fromtimestamp(stat.st_mtime).isoformat(),
                "type": "pg" if fname.startswith("pg_") else ("qdrant" if fname.startswith("qdrant_") else "other"),
                "location": "local",
                "azure_url": None,
            })

    # 2. Listar blobs Azure (folder backups/)
    azure_blobs = []
    from services.storage_service import storage_service as _ss
    if _ss and _ss._azure_container:
        try:
            blobs = _ss._azure_container.list_blobs(name_starts_with="backups/")
            sas_token = "?" + _ss.sas_url.split("?", 1)[1] if _ss.sas_url and "?" in _ss.sas_url else ""
            for b in blobs:
                if b.name.startswith("backups/"):
                    bname = b.name.split("/", 1)[1]
                    azure_blobs.append({
                        "file": bname,
                        "size": b.size or 0,
                        "size_human": f"{(b.size or 0) / 1024 / 1024:.2f} MB" if (b.size or 0) >= 1024*1024 else f"{(b.size or 0) / 1024:.1f} KB",
                        "modified": b.last_modified.isoformat() if b.last_modified else None,
                        "type": "azure_zip",
                        "azure_url": f"{_ss._azure_container.url}/{bname}{sas_token}",
                        "etag": b.etag or None,
                    })
        except Exception as e:
            logger.warning(f"⚠️ Falha ao listar Azure backups: {e}")

    # 3. Fazer merge: marca cada arquivo local com `in_azure: bool` se existir um blob zip do mesmo timestamp
    #    O blob no Azure é um ZIP único do par pg+qdrant do mesmo timestamp.
    #    Match por timestamp YYYYMMDD_HHMMSS presente tanto nos files locais quanto no nome do zip.
    import re as _re
    ts_re = _re.compile(r"(\d{8}_\d{6})")
    for b in azure_blobs:
        m = ts_re.search(b["file"])
        if not m:
            continue
        ts = m.group(1)
        # Marca cada arquivo local que tem esse timestamp como `in_azure=True`
        for local_file in files:
            local_ts = ts_re.search(local_file["file"])
            if local_ts and local_ts.group(1) == ts:
                local_file["in_azure"] = True
                local_file["azure_url"] = b["azure_url"]
                local_file["location"] = "local+azure"

    # Ordena por modified desc
    files.sort(key=lambda x: x.get("modified") or "", reverse=True)
    azure_blobs.sort(key=lambda x: x.get("modified") or "", reverse=True)

    return {
        "local": files,
        "azure": azure_blobs,
        "azure_dir": f"{_ss._azure_container.url}/backups" if _ss and _ss._azure_container else None,
        "local_dir": BACKUP_DIR,
        "local_total": len(files),
        "azure_total": len(azure_blobs),
        "retention_days": 30,
    }



@router.post("/db/restore")
async def db_restore(
    payload: dict,
    admin: models.User = Depends(require_admin),
):
    from datetime import datetime as _dt
    """Restaura um backup do Postgres. CUIDADO: sobrescreve banco atual.
    payload = {file: 'pg_20260719_171603.sql.gz', dry_run: true/false}
    Default dry_run=True (só mostra o que seria feito).
    """
    fname = payload.get("file")
    dry_run = payload.get("dry_run", True)

    if not fname or not fname.startswith("pg_") or not fname.endswith(".sql.gz"):
        raise HTTPException(400, "file deve ser um backup pg_*.sql.gz")

    fpath = f"{BACKUP_DIR}/{fname}"
    if not _os.path.isfile(fpath):
        raise HTTPException(404, f"Arquivo não encontrado: {fpath}")

    pg_pass = (await db.execute(text("SELECT current_setting('postgres_password')"))).scalar() if False else None
    # Pega senha do .env
    import re as _re
    env_text = open("/home/peron/projects/ayria/.env").read()
    m = _re.search(r"^POSTGRES_PASSWORD=(.+)$", env_text, _re.M)
    pg_pass = m.group(1).strip() if m else None
    if not pg_pass:
        raise HTTPException(500, "POSTGRES_PASSWORD não encontrada no .env")

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "message": f"DRY RUN: backup {fname} seria restaurado em /dev/null (não modifica nada)",
            "file": fname,
            "size": _os.path.getsize(fpath),
        }

    # Restore real — CUIDADO!
    logger.warning(
        f"⚠️ RESTORE MANUAL disparado por admin {admin.email}: {fname} (BACKUP ATUAL SERÁ PERDIDO)"
    )
    # Mata conexões existentes
    await db.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'ayria' AND pid <> pg_backend_pid()"))
    await db.commit()

    try:
        # gunzip + psql
        cmd = f"gunzip -c {fpath} | PGPASSWORD='{pg_pass}' psql -h 127.0.0.1 -p 5434 -U ayria -d ayria"
        result = _sp.run(
            ["bash", "-c", cmd],
            capture_output=True, text=True, timeout=600,  # 10min
        )
        return {
            "ok": result.returncode == 0,
            "dry_run": False,
            "returncode": result.returncode,
            "stderr": result.stderr[-2000:] if result.stderr else "",
        }
    except _sp.TimeoutExpired:
        raise HTTPException(500, "Restore demorou mais que 10min (timeout)")
    except Exception as e:
        raise HTTPException(500, f"Erro no restore: {e}")


# ============================================================
# FRONTEND ERROR INGEST — recebe erros do frontend e grava no log
# ============================================================
import traceback as _tb

_frontend_logger = logging.getLogger("ayria.frontend")


class FrontendLogEvent(BaseModel):
    """Evento de erro reportado pelo frontend."""
    level: str = "error"  # error | warn | info
    source: Optional[str] = None  # ex: "AdminPage", "ChatPage"
    context: Optional[str] = None  # ex: "loadUsers", "sendMessage"
    message: str
    data: Optional[dict] = None
    url: Optional[str] = None
    user_agent: Optional[str] = None


@router.post("/log/event", status_code=201)
async def ingest_frontend_log(
    event: FrontendLogEvent,
    request: Request,
    admin: models.User = Depends(require_admin),
):
    """
    Recebe evento de erro do frontend e grava no log do backend.
    Assim o módulo `logs` vê erros do frontend também.
    """
    ip = request.client.host if request.client else "?"
    payload = {
        "source": event.source,
        "context": event.context,
        "message": event.message,
        "data": event.data,
        "url": event.url,
        "ip": ip,
        "user_agent": event.user_agent,
    }
    msg = f"[FRONTEND] {event.source or '?'}/{event.context or '?'} | {event.message}"

    if event.level == "error":
        _frontend_logger.error("%s | %s", msg, json.dumps(payload, ensure_ascii=False, default=str))
    elif event.level == "warn":
        _frontend_logger.warning("%s | %s", msg, json.dumps(payload, ensure_ascii=False, default=str))
    else:
        _frontend_logger.info("%s | %s", msg, json.dumps(payload, ensure_ascii=False, default=str))

    return {"ok": True, "logged": event.level}


# ============================================================
# 19/07/2026 — RATE LIMIT DASHBOARD (Security Tab)
# ============================================================
from sqlalchemy import text as _text
import json as _json
from datetime import datetime as _dt, timedelta as _td

from services.rate_limiter import (
    STORE, CONFIG, log_event as _log_event,
    get_blacklist, add_blacklist, remove_blacklist,
    lookup_geo as _lookup_geo,
)
from services.rate_limiter import is_blacklisted as _is_blacklisted


@router.get("/security/rate-limit/status", response_model=schemas.RateLimitStatusResponse)
async def rl_status(admin: models.User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """Resumo agregado: IPs bloqueados, em alerta, falhas 24h, blocks 24h."""
    snap = STORE.snapshot()
    blocked_now = len(snap["blocked"])
    in_alert = len(snap["alert"])

    # 24h stats do banco
    result = await db.execute(_text("""
        SELECT
            SUM(CASE WHEN success = FALSE THEN 1 ELSE 0 END) AS failures_24h,
            SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) AS successes_24h
        FROM rate_limit_events
        WHERE occurred_at > NOW() - INTERVAL '24 hours'
    """))
    row = result.first()
    total_failures_24h = (row[0] or 0) if row else 0

    # blocks 24h = events whose ip ficou bloqueado (não temos este campo armazenado,
    # então aproximamos: eventos falha com ip que aparece no snapshot blocked + os já liberados).
    # Para simplicidade, contamos falhas com >5 ocorrências em 60s nos últimos 24h.
    result2 = await db.execute(_text("""
        SELECT COUNT(*) FROM (
            SELECT ip, COUNT(*) AS cnt
            FROM rate_limit_events
            WHERE success = FALSE AND occurred_at > NOW() - INTERVAL '24 hours'
            GROUP BY ip
            HAVING COUNT(*) >= 5
        ) t
    """))
    total_blocks_24h = result2.scalar() or 0

    return schemas.RateLimitStatusResponse(
        ips_blocked_now=blocked_now,
        ips_in_alert=in_alert,
        total_failures_24h=int(total_failures_24h),
        total_blocks_24h=int(total_blocks_24h),
        paused=False,
    )


@router.get("/security/rate-limit/active", response_model=schemas.RateLimitBlockedList)
async def rl_active(admin: models.User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """IPs atualmente bloqueados em memória."""
    import time as _t
    snap = STORE.snapshot()
    items = []
    for entry in snap["blocked"]:
        # Geo lookup assíncrono (fire and forget pra não bloquear)
        geo = await _lookup_geo(entry["ip"])

        # Tenta pegar o último email_attempted + user_agent do banco
        result = await db.execute(_text("""
            SELECT email_attempted, user_agent FROM rate_limit_events
            WHERE ip = CAST(:ip AS INET)
            ORDER BY occurred_at DESC LIMIT 1
        """), {"ip": entry["ip"]})
        last = result.first()
        items.append(schemas.RateLimitBlockedIP(
            ip=entry["ip"],
            endpoint=entry["endpoint"],
            geo=geo,
            failures_in_window=entry["failures_in_window"],
            retry_in_seconds=entry["retry_in_seconds"],
            blocked_until_epoch=entry["blocked_until"],
            blocked_until_iso=_dt.fromtimestamp(entry["blocked_until"]).isoformat(),
            user_agent=last[1] if last else None,
            last_email_attempted=last[0] if last else None,
        ))
    return schemas.RateLimitBlockedList(items=items, total=len(items))


@router.get("/security/rate-limit/alert", response_model=schemas.RateLimitAlertList)
async def rl_alert(admin: models.User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """IPs com falhas recentes mas ainda não bloqueados."""
    snap = STORE.snapshot()
    items = []
    for entry in snap["alert"]:
        geo = await _lookup_geo(entry["ip"])
        result = await db.execute(_text("""
            SELECT user_agent FROM rate_limit_events
            WHERE ip = CAST(:ip AS INET)
            ORDER BY occurred_at DESC LIMIT 1
        """), {"ip": entry["ip"]})
        last = result.first()
        items.append(schemas.RateLimitAlertIP(
            ip=entry["ip"],
            endpoint=entry["endpoint"],
            geo=geo,
            failures_in_window=entry["failures_in_window"],
            user_agent=last[0] if last else None,
        ))
    return schemas.RateLimitAlertList(items=items, total=len(items))


@router.get("/security/rate-limit/events", response_model=schemas.RateLimitEventsPage)
async def rl_events(
    admin: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    only_failures: bool = Query(True),
):
    """Últimos eventos (terminal-like, scroll infinito)."""
    where_clause = "WHERE success = FALSE" if only_failures else ""
    result = await db.execute(_text(f"""
        SELECT id, ip::text, endpoint, success, email_attempted,
               user_agent, occurred_at
        FROM rate_limit_events
        {where_clause}
        ORDER BY occurred_at DESC
        LIMIT :lim
    """), {"lim": limit})
    items = []
    for r in result.fetchall():
        items.append({
            "id": r[0], "ip": r[1], "endpoint": r[2], "success": r[3],
            "email_attempted": r[4], "user_agent": r[5],
            "occurred_at": r[6].isoformat() if r[6] else None,
        })
    total_q = await db.execute(_text(f"SELECT COUNT(*) FROM rate_limit_events {where_clause}"))
    total = total_q.scalar() or 0
    return schemas.RateLimitEventsPage(items=items, total=int(total))


@router.post("/security/rate-limit/unblock")
async def rl_unblock(
    payload: schemas.RateLimitUnblockRequest,
    admin: models.User = Depends(require_admin),
):
    """Desbloqueio manual de um IP."""
    cleared = await STORE.unblock(payload.ip, payload.endpoint)
    logger.info(f"admin {admin.email} desbloqueou ip={payload.ip} endpoint={payload.endpoint} cleared={cleared}")
    return {"ok": True, "ip": payload.ip, "cleared_entries": cleared}


@router.get("/security/blacklist", response_model=schemas.BlacklistResponse)
async def rl_blacklist_list(admin: models.User = Depends(require_admin)):
    items = await get_blacklist()
    return schemas.BlacklistResponse(items=[schemas.BlacklistItem(**i) for i in items], total=len(items))


@router.post("/security/blacklist")
async def rl_blacklist_add(
    payload: schemas.BlacklistAddRequest,
    admin: models.User = Depends(require_admin),
):
    await add_blacklist(
        ip=payload.ip,
        reason=payload.reason or "Sem motivo",
        added_by=admin.email,
        expires_at=payload.expires_at,
    )
    logger.info(f"admin {admin.email} adicionou blacklist ip={payload.ip} reason={payload.reason}")
    # Também limpa da memória pra forçar nova checagem
    await STORE.unblock(payload.ip)
    return {"ok": True, "ip": payload.ip}


@router.delete("/security/blacklist/{ip:str}")
async def rl_blacklist_remove(
    ip: str,
    admin: models.User = Depends(require_admin),
):
    rows = await remove_blacklist(ip)
    logger.info(f"admin {admin.email} removeu blacklist ip={ip} rows={rows}")
    return {"ok": True, "ip": ip, "removed": rows}


@router.get("/security/rate-limit/config", response_model=schemas.RateLimitConfigResponse)
async def rl_config(admin: models.User = Depends(require_admin)):
    return schemas.RateLimitConfigResponse(
        login={
            "max_failures": CONFIG["/auth/login"].max_failures,
            "window_seconds": CONFIG["/auth/login"].window_seconds,
            "block_seconds": CONFIG["/auth/login"].block_seconds,
        },
        register={
            "max_failures": CONFIG["/auth/register"].max_failures,
            "window_seconds": CONFIG["/auth/register"].window_seconds,
            "block_seconds": CONFIG["/auth/register"].block_seconds,
        },
        forgot_password={
            "max_failures": CONFIG["/auth/forgot-password"].max_failures,
            "window_seconds": CONFIG["/auth/forgot-password"].window_seconds,
            "block_seconds": CONFIG["/auth/forgot-password"].block_seconds,
        },
    )


# ============================================================
# /api/admin/security/rate-limit/_inject — DEV/TEST ONLY (19/07/2026)
# Admin pode injetar falhas em IP fictício pra ver o dashboard funcionar.
# Em prod isso vira seed automático de logs reais.
# ============================================================
class RateLimitInjectRequest(BaseModel):
    ip: str
    endpoint: str = "/auth/login"
    failures: int = 5
    blocked: bool = True


@router.post("/security/rate-limit/_inject")
async def rl_inject(
    payload: RateLimitInjectRequest,
    admin: models.User = Depends(require_admin),
):
    """Dev only: injeta N falhas em IP fictício pra visualização no dashboard."""
    ip = payload.ip
    ep = payload.endpoint
    for _ in range(payload.failures):
        await STORE.record_failure(ip, ep)
    cleared = 0
    if not payload.blocked:
        cleared = await STORE.unblock(ip, ep)
    return {"ok": True, "ip": ip, "failures_injected": payload.failures, "blocked": payload.blocked, "cleared_entries": cleared}
