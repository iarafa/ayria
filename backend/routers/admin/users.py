"""
admin/users.py — CRUD de usuários + block + password + role + details + observer

Endpoints:
  GET    /users                              → listar
  POST   /users                              → criar
  PUT    /users/{id}                         → editar (full_name, is_active, plano)
  DELETE /users/{id}                         → excluir completo (LGPD-style)
  POST   /users/{id}/block                   → bloquear/desbloquear
  POST   /users/{id}/password                → admin reseta senha
  PUT    /users/{id}/role                    → trocar role (SUPER_ADMIN only)
  GET    /users/{id}/details                 → tudo sobre 1 user
  GET    /users/{id}/chats                   → listar chats do user (observer)
  GET    /users/{id}/chats/{chat_id}/messages → listar mensagens (observer)
"""
from ._base import (
    APIRouter, Depends, HTTPException, Request,
    select, func, desc,
    uuid, logging, datetime, timedelta, timezone, Optional,
    get_db, require_admin, hash_password, get_client_ip, get_user_agent,
    credit_service, models, schemas,
)
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])


# ============================================================
# USERS
# ============================================================
@router.get("/users", response_model=list[schemas.AdminUserResponse])
async def list_users(
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
    role: Optional[str] = None,
):
    """Lista todos os usuários (admin) - inclui plano + saldo de créditos.
    ?role=admin filtra só admins (usado pela aba 'Administradores')."""
    stmt = select(models.User).order_by(models.User.created_at.desc())
    if role:
        stmt = stmt.where(models.User.role == role)
    res = await db.execute(stmt)
    users = res.scalars().all()

    result = []
    for u in users:
        count_res = await db.execute(
            select(func.count(models.Message.id)).where(models.Message.user_id == u.id)
        )
        count = count_res.scalar() or 0

        plan = None
        if u.selected_plan_id:
            plan_res = await db.execute(
                select(models.Plan).where(models.Plan.id == u.selected_plan_id)
            )
            plan = plan_res.scalar_one_or_none()

        result.append(schemas.AdminUserResponse(
            id=u.id, email=u.email, full_name=u.full_name, role=u.role,
            is_active=u.is_active, onboarding_status=u.onboarding_status or "pending",
            created_at=u.created_at, last_login_at=u.last_login_at,
            message_count=count,
            selected_plan_id=u.selected_plan_id,
            selected_plan_slug=plan.slug if plan else None,
            selected_plan_name=plan.name if plan else None,
            credit_balance=u.credit_balance or 0,
            credit_status=u.credit_status or "inactive",
            plan_selected_at=u.plan_selected_at,
            billing_status=u.billing_status or "billing_not_enabled",
            credits_last_granted_at=u.credits_last_granted_at,
        ))
    return result


@router.post("/users", response_model=schemas.AdminUserResponse, status_code=201)
async def create_user(
    payload: schemas.UserRegister,
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Admin cria novo usuário. Pode passar role=SUPER_ADMIN no payload se quiser criar admin.
    Aceita plan_slug (default: basico) - concede créditos iniciais via service idempotente."""
    existing = await db.execute(
        select(models.User).where(models.User.email == payload.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    requested_role = getattr(payload, "role", "user")
    if requested_role not in ("user", "SUPER_ADMIN"):
        requested_role = "user"

    plan_slug = getattr(payload, "plan_slug", None) or "basico"
    plan = await credit_service.get_plan_by_slug(db, plan_slug)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Plano '{plan_slug}' não encontrado")

    user = models.User(
        id=uuid.uuid4(),
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=requested_role,
        is_active=True,
        is_verified=True,
        onboarding_status="pending",
        selected_plan_id=plan.id,
        plan_selected_at=datetime.utcnow(),
        credit_status="active",
        billing_status="billing_not_enabled",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

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
    db=Depends(get_db),
):
    """Edita nome, is_active OU troca plano de um usuário (NÃO muda role).
    Se selected_plan_slug for informado e diferente do atual, troca o plano + registra transaction."""
    res = await db.execute(select(models.User).where(models.User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Você não pode editar a si mesmo")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active

    if payload.selected_plan_slug is not None:
        new_plan = await credit_service.get_plan_by_slug(db, payload.selected_plan_slug)
        if not new_plan:
            raise HTTPException(status_code=400, detail=f"Plano '{payload.selected_plan_slug}' não encontrado")

        if user.selected_plan_id != new_plan.id:
            old_plan = None
            if user.selected_plan_id:
                old_res = await db.execute(
                    select(models.Plan).where(models.Plan.id == user.selected_plan_id)
                )
                old_plan = old_res.scalar_one_or_none()

            old_credits = old_plan.credits if old_plan else 0
            delta = new_plan.credits - old_credits
            balance_before = user.credit_balance or 0
            new_balance = max(0, balance_before + delta)

            user.selected_plan_id = new_plan.id
            user.plan_selected_at = datetime.utcnow()
            user.credit_balance = new_balance

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
    db=Depends(get_db),
):
    """Bloqueia/desbloqueia um usuário.
    Duration: "1h", "24h", "permanent", "unblock"
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
        user.blocked_until = None
        user.blocked_by = admin.id
        user.block_reason = payload.reason
        user.is_active = False
        logger.warning(f"🚫⛔ User {user.email} BLOCKED PERMANENTLY by {admin.email}: {payload.reason}")
    else:
        raise HTTPException(status_code=400, detail=f"duration inválida: {payload.duration}")

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
    db=Depends(get_db),
):
    """Admin reseta senha de um user (sem precisar da senha antiga)."""
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Senha deve ter no mínimo 8 caracteres.",
        )

    user_res = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Use o endpoint próprio (/api/auth/me/password) pra trocar SUA senha.",
        )

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

    old_hash_prefix = (user.password_hash or "")[:20]
    user.password_hash = hash_password(payload.new_password)
    await db.commit()
    await db.refresh(user)

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


@router.put("/users/{user_id}/role", response_model=schemas.AdminUserResponse)
async def update_user_role(
    user_id: uuid.UUID,
    payload: schemas.AdminRoleUpdate,
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Troca role de um usuário. APENAS SUPER_ADMIN pode promover/rebaixar admins."""
    if admin.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Apenas SUPER_ADMIN pode alterar roles",
        )

    if payload.new_role not in ("user", "admin", "SUPER_ADMIN"):
        raise HTTPException(
            status_code=400,
            detail=f"Role inválida: {payload.new_role}",
        )

    res = await db.execute(select(models.User).where(models.User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    old_role = user.role
    if old_role == payload.new_role:
        return user

    if user_id == admin.id and payload.new_role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=400,
            detail="Você não pode rebaixar a si mesmo",
        )

    if old_role == "SUPER_ADMIN" and payload.new_role != "SUPER_ADMIN":
        res_count = await db.execute(
            select(func.count(models.User.id)).where(models.User.role == "SUPER_ADMIN")
        )
        super_count = res_count.scalar() or 0
        if super_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Não é possível rebaixar o último SUPER_ADMIN",
            )

    user.role = payload.new_role
    user.updated_at = datetime.now(timezone.utc)

    audit = models.AuditLog(
        user_id=admin.id,
        action="role_change",
        details={
            "actor_user_id": str(admin.id),
            "actor_email": admin.email,
            "target_user_id": str(user.id),
            "target_email": user.email,
            "old_role": old_role,
            "new_role": payload.new_role,
            "reason": payload.reason or "",
        },
    )
    db.add(audit)

    await db.commit()
    await db.refresh(user)

    logger.info(
        f"✅ Role de {user.email} alterada: {old_role} → {payload.new_role} por {admin.email}"
    )

    return user


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Exclui um usuário E TODOS os dados dele (LGPD-style):
    - PostgreSQL: user_profiles, user_attributes, chats, messages, audit (anonimizado)
    - Qdrant: TODAS as memórias (memoria_episodica)
    - Stripe: invoices + subscriptions + redemptions
    """
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir a si mesmo")

    res = await db.execute(select(models.User).where(models.User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.role in ("admin", "SUPER_ADMIN") and admin.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Apenas SUPER_ADMIN pode excluir outros administradores",
        )
    if user.role == "SUPER_ADMIN":
        res_count = await db.execute(
            select(func.count(models.User.id)).where(models.User.role == "SUPER_ADMIN")
        )
        super_count = res_count.scalar() or 0
        if super_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Não é possível excluir o último SUPER_ADMIN do sistema",
            )

    deleted_summary = {"pg": {}, "qdrant": 0}

    try:
        r = await db.execute(text("DELETE FROM user_profiles WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["user_profiles"] = r.rowcount

        r = await db.execute(text("DELETE FROM user_attributes WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["user_attributes"] = r.rowcount

        r = await db.execute(text("DELETE FROM messages WHERE chat_id IN (SELECT id FROM chats WHERE user_id = :uid)"), {"uid": str(user_id)})
        deleted_summary["pg"]["messages"] = r.rowcount

        r = await db.execute(text("DELETE FROM chats WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["chats"] = r.rowcount

        r = await db.execute(text("UPDATE audit_log SET user_id = NULL WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["audit_log_anonymized"] = r.rowcount

        r = await db.execute(text("DELETE FROM stripe_invoices WHERE ayria_user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["stripe_invoices"] = r.rowcount
        r = await db.execute(text("DELETE FROM stripe_subscriptions WHERE ayria_user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["stripe_subscriptions"] = r.rowcount

        r = await db.execute(text("DELETE FROM coupon_redemptions WHERE user_id = :uid"), {"uid": str(user_id)})
        deleted_summary["pg"]["coupon_redemptions"] = r.rowcount

        from services.vector_service import vector_service
        deleted_summary["qdrant"] = await vector_service.delete_user_memories(str(user_id))

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
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao excluir usuário. Tente novamente ou contate o suporte."
        )


# ============================================================
# DETALHES COMPLETOS DE UM USUÁRIO (admin)
# ============================================================
@router.get("/users/{user_id}/details", response_model=schemas.AdminUserDetailResponse)
async def get_user_details(
    user_id: uuid.UUID,
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Retorna TUDO sobre um usuário: dados básicos, plano, créditos, perfil de onboarding,
    numerologia, astrologia, atributos dinâmicos, contagens de uso."""
    res = await db.execute(select(models.User).where(models.User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    plan = None
    if user.selected_plan_id:
        plan_res = await db.execute(select(models.Plan).where(models.Plan.id == user.selected_plan_id))
        plan = plan_res.scalar_one_or_none()

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

    tx_count_res = await db.execute(
        select(func.count(models.CreditTransaction.id)).where(models.CreditTransaction.user_id == user_id)
    )
    tx_count = tx_count_res.scalar() or 0

    profile_attrs = None
    prof_res = await db.execute(select(models.UserProfile).where(models.UserProfile.user_id == user_id))
    profile = prof_res.scalar_one_or_none()
    if profile:
        profile_attrs = profile.attributes

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
# OBSERVADOR - admin lê conversas/messages de OUTRO user (read-only)
# Cada acesso é registrado em audit_log (LGPD compliance)
# ============================================================
async def _log_admin_view(admin, target_user_id: str, action: str, details: dict, db):
    """Helper: registra acesso de admin a dados de outro user (LGPD audit trail)."""
    from models import AuditLog
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
    db=Depends(get_db),
):
    """Admin lista conversas de um user (MODO OBSERVADOR - read-only)."""
    target_res = await db.execute(select(models.User).where(models.User.id == user_id))
    target = target_res.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

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
    db=Depends(get_db),
):
    """Admin lista mensagens de um chat de um user (MODO OBSERVADOR - read-only)."""
    chat_res = await db.execute(
        select(models.Chat).where(
            models.Chat.id == chat_id,
            models.Chat.user_id == user_id,
        )
    )
    chat = chat_res.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Conversa não encontrada para este usuário")

    res = await db.execute(
        select(models.Message)
        .where(models.Message.chat_id == chat_id)
        .order_by(models.Message.created_at)
    )
    messages = res.scalars().all()
    msgs = []
    for m in messages:
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
