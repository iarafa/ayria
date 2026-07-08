"""
AYRIA - Onboarding Router (ALINHADO COM CHECKLIST OFICIAL)

- Salva respostas em user_attributes (NAO em profile.attributes JSONB)
- Calcula numerologia COMPLETA quando coleta data_nascimento + nome_completo
- Atualiza users.numerology_data
- Marca onboarding_status='completed' ao terminar
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict
import logging

from database import get_db
from utils.security import get_current_user
from services.numerology_service import calcular_mapa_completo, gerar_relatorio_numerologico
from services.astrology_service import astrology_service
import models
import schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.get("/status", response_model=schemas.OnboardingStatus)
async def get_status(
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna status + perguntas dinâmicas + respostas já dadas"""
    # Carrega perfil
    profile_res = await db.execute(
        select(models.UserProfile).where(models.UserProfile.user_id == user.id)
    )
    profile = profile_res.scalar_one_or_none()

    # Carrega respostas já salvas em user_attributes (com JOIN pra pegar attribute_code da definition)
    answered_res = await db.execute(
        select(models.UserAttribute, models.AttributeDefinition)
        .join(models.AttributeDefinition, models.UserAttribute.attribute_definition_id == models.AttributeDefinition.id)
        .where(models.UserAttribute.user_id == user.id)
    )
    answered_attrs = {attr_def.code: ua.value for ua, attr_def in answered_res.all()}

    # Carrega status de cada atributo (pra filtrar o que ainda precisa de resposta)
    attr_status_res = await db.execute(
        select(models.UserAttribute, models.AttributeDefinition)
        .join(models.AttributeDefinition, models.UserAttribute.attribute_definition_id == models.AttributeDefinition.id)
        .where(models.UserAttribute.user_id == user.id)
    )
    attr_status_map = {attr_def.code: ua.status for ua, attr_def in attr_status_res.all()}

    # Carrega perguntas ativas
    questions_res = await db.execute(
        select(models.OnboardingConfig)
        .where(models.OnboardingConfig.is_active == True)
        .order_by(models.OnboardingConfig.step)
    )
    all_questions = questions_res.scalars().all()

    # 🛡️ FIX: se user JÁ TEM onboarding_status='completed' (admin bypass, ou user finalizou),
    # não devolver perguntas mesmo que user_attributes esteja vazio
    if (user.onboarding_status or "").lower() == "completed":
        return schemas.OnboardingStatus(
            status="completed",
            current_step=len(all_questions) + 1,
            total_steps=len(all_questions),
            numerology_data=user.numerology_data,
            questions=[],
            answered={},
        )

    # FILTRA: mostra só perguntas que ainda não foram respondidas/puladas/adiadas
    TERMINAL_STATUSES = {'answered', 'skipped', 'pending_next_chat', 'snoozed'}
    questions = [
        q for q in all_questions
        if attr_status_map.get(q.attribute_code) not in TERMINAL_STATUSES
    ]

    # Step atual = quantas respostas TERMINAIS já tem + 1
    terminal_count = sum(1 for s in attr_status_map.values() if s in TERMINAL_STATUSES)
    current_step = terminal_count + 1

    return schemas.OnboardingStatus(
        status=user.onboarding_status or "pending",
        current_step=current_step,
        total_steps=len(all_questions),
        numerology_data=user.numerology_data,
        questions=[
            {
                "step": q.step,
                "question_text": q.question_text,
                "helper_text": q.helper_text,
                "question_type": q.question_type,
                "attribute_code": q.attribute_code,
                "options": q.options,
                "conditional_show": q.conditional_show,
            }
            for q in questions
        ],
        answered=answered_attrs,
    )


@router.post("/answer", response_model=schemas.OnboardingAnswerResponse)
async def post_answer(
    payload: schemas.OnboardingAnswer,
    background_tasks: BackgroundTasks,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Salva resposta de uma pergunta de onboarding.

    Ações suportadas (payload.action):
    - 'answer' (default): salva o valor como respondido (status='answered')
    - 'skip': pular permanentemente (status='skipped')
    - 'later': responder depois (status='pending_next_chat' → Sistema 2)
    - 'continue_without': user confirmou que segue sem (status='skipped')
    - 'snooze': adiar X horas (status='snoozed')
    """
    if not payload.attribute_code:
        raise HTTPException(status_code=400, detail="attribute_code obrigatório")

    # Garante que profile existe
    profile_res = await db.execute(
        select(models.UserProfile).where(models.UserProfile.user_id == user.id)
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        profile = models.UserProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            attributes={},
            onboarding_completed=False,
        )
        db.add(profile)
        await db.flush()

    # 1. UPSERT em user_attributes
    # Primeiro: garantir que attribute_definition existe (cria se necessário)
    def_res = await db.execute(
        select(models.AttributeDefinition).where(
            models.AttributeDefinition.code == payload.attribute_code
        )
    )
    attr_def = def_res.scalar_one_or_none()
    if not attr_def:
        attr_def = models.AttributeDefinition(
            id=uuid.uuid4(),
            code=payload.attribute_code,
            label=payload.attribute_code.replace("_", " ").title(),
            attribute_type="text",
            is_required=False,
            is_active=True,
        )
        db.add(attr_def)
        await db.flush()

    # UPSERT user_attribute
    attr_res = await db.execute(
        select(models.UserAttribute).where(
            models.UserAttribute.user_id == user.id,
            models.UserAttribute.attribute_definition_id == attr_def.id,
        )
    )
    existing = attr_res.scalar_one_or_none()

    # Determina status baseado na ação do user
    action = payload.action or 'answer'
    now = datetime.utcnow()

    if action == 'skip' or action == 'continue_without':
        # Pular — NÃO pergunta de novo nesse onboarding, valor fica em branco
        new_status = 'skipped'
        if existing:
            existing.value = None
            existing.status = new_status
            existing.skipped_at = now
            existing.updated_at = now
        else:
            new_attr = models.UserAttribute(
                id=uuid.uuid4(),
                user_id=user.id,
                attribute_definition_id=attr_def.id,
                value=None,
                status=new_status,
                skipped_at=now,
            )
            db.add(new_attr)
    elif action == 'later':
        # Responder depois — vai pra fila do Sistema 2
        new_status = 'pending_next_chat'
        if existing:
            existing.value = None
            existing.status = new_status
            existing.last_asked_at = now
            existing.updated_at = now
        else:
            new_attr = models.UserAttribute(
                id=uuid.uuid4(),
                user_id=user.id,
                attribute_definition_id=attr_def.id,
                value=None,
                status=new_status,
                last_asked_at=now,
            )
            db.add(new_attr)
    elif action == 'snooze':
        # Adiar por X horas
        snooze_hours = payload.snooze_hours or 24
        snooze_until = now + timedelta(hours=snooze_hours)
        new_status = 'snoozed'
        if existing:
            existing.value = existing.value
            existing.status = new_status
            existing.snooze_until = snooze_until
            existing.updated_at = now
        else:
            new_attr = models.UserAttribute(
                id=uuid.uuid4(),
                user_id=user.id,
                attribute_definition_id=attr_def.id,
                value=None,
                status=new_status,
                snooze_until=snooze_until,
            )
            db.add(new_attr)
    else:
        # Responder normalmente (action='answer')
        new_status = 'answered'
        if existing:
            existing.value = payload.value
            existing.status = new_status
            existing.skipped_at = None
            existing.snooze_until = None
            existing.updated_at = now
        else:
            new_attr = models.UserAttribute(
                id=uuid.uuid4(),
                user_id=user.id,
                attribute_definition_id=attr_def.id,
                value=payload.value,
                status=new_status,
            )
            db.add(new_attr)

    # 2. Sincroniza em profile.attributes APENAS se for answered
    attrs_jsonb = dict(profile.attributes or {})
    if new_status == 'answered':
        attrs_jsonb[payload.attribute_code] = payload.value
    profile.attributes = attrs_jsonb

    # 3. Atualiza status
    if user.onboarding_status == "pending":
        user.onboarding_status = "in_progress"

    # 4. Verifica se completou TODAS perguntas
    # Considera como "respondida" tudo que NÃO é pending
    total_questions_res = await db.execute(
        select(func.count(models.OnboardingConfig.id))
        .where(models.OnboardingConfig.is_active == True)
    )
    total_questions = total_questions_res.scalar() or 0

    answered_count_res = await db.execute(
        select(func.count(models.UserAttribute.id))
        .where(
            models.UserAttribute.user_id == user.id,
            # Status TERMINAIS — todos não-pending contam como "tratados"
            # para fins de completar o onboarding (later vai pra chat, skipped nunca pergunta)
            models.UserAttribute.status.in_(['answered', 'skipped', 'snoozed', 'pending_next_chat'])
        )
    )
    answered_count = answered_count_res.scalar() or 0

    # Mensagem de aviso quando user pula (sobre limitação de interpretação)
    warning_message = None
    if action == 'skip':
        # Só adiciona aviso na PRIMEIRA vez que pula (não em 'continue_without' que é confirmação)
        if action == 'skip' and (not existing or existing.status != 'skipped'):
            warning_message = (
                "Tudo bem! Mas saiba que sem essa informação, posso não te "
                "interpretar tão bem. Quer continuar mesmo assim, ou prefere "
                "responder depois?"
            )

    numerology_calculated = False
    if answered_count >= total_questions:
        user.onboarding_status = "completed"
        profile.onboarding_completed = True
        profile.completed_at = datetime.utcnow()

        # Marca como "calculando perfil" - frontend fica em tela cinematográfica
        user.profile_status = "calculating"

        # Calcula em BACKGROUND (numerologia + astrologia silenciosos)
        # Frontend faz polling em /api/profile/status até 'ready'
        background_tasks.add_task(
            calcular_perfil_completo_background,
            user_id=str(user.id),
            attrs=attrs_jsonb,
        )
        numerology_calculated = True
        logger.info(
            f"✅ Onboarding completo para user {user.email} - cálculo de perfil em background"
        )

    await db.commit()
    await db.refresh(user)

    return schemas.OnboardingAnswerResponse(
        status=user.onboarding_status,
        completed=user.onboarding_status == "completed",
        numerology_data=user.numerology_data,
        numerology_calculated=numerology_calculated,
        progress=f"{answered_count}/{total_questions}",
        profile_status=user.profile_status,
        warning_message=warning_message,
    )


async def calcular_perfil_completo_background(user_id: str, attrs: Dict[str, Any]):
    """
    Calcula numerologia + astrologia em BACKGROUND.
    User NÃO é notificado — é invisível.
    """
    from database import AsyncSessionLocal

    try:
        # 1. Numerologia (sempre funciona, é matemática pura)
        try:
            mapa_num = calcular_mapa_completo(attrs)
        except Exception as e:
            logger.error(f"Erro numerologia: {e}")
            mapa_num = None

        # 2. Astrologia (precisa data + hora + local)
        try:
            data_nasc = attrs.get("data_nascimento")
            hora_nasc = attrs.get("hora_nascimento") or "12:00"
            cidade = attrs.get("local_nascimento") or "São Paulo"
            nome = attrs.get("nome_completo") or "User"

            mapa_ast = None
            if data_nasc:
                mapa_ast = astrology_service.calcular_mapa(
                    nome=nome,
                    data_nascimento=data_nasc,
                    hora_nascimento=hora_nasc,
                    cidade=cidade,
                )
        except Exception as e:
            logger.error(f"Erro astrologia: {e}")
            mapa_ast = None

        # 3. Salva tudo no user
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(models.User).where(models.User.id == uuid.UUID(user_id)))
            user = res.scalar_one_or_none()
            if user:
                if mapa_num:
                    user.numerology_data = mapa_num
                if mapa_ast:
                    user.astrology_data = mapa_ast
                user.profile_status = "ready" if (mapa_num or mapa_ast) else "failed"
                await db.commit()
                logger.info(
                    f"✅ Perfil completo salvo para {user.email}: "
                    f"num={'OK' if mapa_num else 'NÃO'} ast={'OK' if mapa_ast else 'NÃO'}"
                )

        # 4. 🆕 08/07/2026 — Auto-gerar 1ª SUB-ALMA do user (individual)
        # Roda em background, AUTO-APROVADA (é só rascunho inicial).
        try:
            from services.sub_alma_service import generate_user_sub_alma
            async with AsyncSessionLocal() as db:
                # Verifica se já existe (safety — não duplica)
                from sqlalchemy import select as _sel, and_ as _and
                exists_res = await db.execute(
                    _sel(models.UserAlma).where(models.UserAlma.user_id == uuid.UUID(user_id))
                )
                if not exists_res.scalar_one_or_none():
                    await generate_user_sub_alma(
                        db,
                        user_id=uuid.UUID(user_id),
                        trigger="onboarding_complete",
                        created_by=None,  # auto
                        auto_approve=True,
                    )
        except Exception as _e:
            logger.error(f"❌ Falha ao gerar sub-alma inicial do user {user_id}: {_e}")
    except Exception as e:
        logger.error(f"❌ Erro crítico no background de perfil: {e}")
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(models.User).where(models.User.id == uuid.UUID(user_id)))
            user = res.scalar_one_or_none()
            if user:
                user.profile_status = "failed"
                await db.commit()


@router.get("/numerology", response_model=schemas.NumerologyResponse)
async def get_numerology(
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna mapa numerológico calculado + relatório narrativo"""
    mapa = user.numerology_data
    if not mapa:
        raise HTTPException(status_code=404, detail="Numerologia ainda não calculada")

    relatorio = gerar_relatorio_numerologico(mapa)
    return schemas.NumerologyResponse(
        mapa=mapa,
        relatorio=relatorio,
    )

# =====================================================================
# PROFILE STATUS (polling pra tela "Criando seu perfil...")
# =====================================================================
@router.get("/profile/status")
async def get_profile_status(
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna status do cálculo do perfil.
    Frontend faz polling até status='ready' ou 'failed'.

    Auto-fix: se onboarding já está 'completed' mas profile_status é 'pending'
    (caso de users antigos/legados que caíram antes do novo fluxo),
    marca como 'ready' automaticamente.
    """
    # Auto-fix para users legados
    if user.onboarding_status == "completed" and (user.profile_status or "pending") == "pending":
        user.profile_status = "ready"
        await db.commit()
        await db.refresh(user)
        logger.info(f"✅ Auto-fix: user {user.email} legado marcado como ready")

    return {
        "profile_status": user.profile_status or "pending",
        "onboarding_status": user.onboarding_status,
        "has_numerology": user.numerology_data is not None,
        "has_astrology": user.astrology_data is not None,
    }


# =====================================================================
# SISTEMA 2 — Perguntas pendentes pra perguntar em chat novo
# =====================================================================
@router.get("/pending", response_model=schemas.PendingQuestionsResponse)
async def get_pending_questions(
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna TODAS as perguntas pendentes do user.
    
    Usado pelo frontend quando user entra num chat novo:
    - Lista perguntas com status 'pending_next_chat' ou 'pending_current_chat'
    - Lista 'snoozed' que já passaram do snooze_until
    """
    now = datetime.utcnow()
    
    # Busca perguntas pendentes
    pending_res = await db.execute(
        select(models.UserAttribute, models.AttributeDefinition)
        .join(models.AttributeDefinition, models.UserAttribute.attribute_definition_id == models.AttributeDefinition.id)
        .where(
            models.UserAttribute.user_id == user.id,
            models.UserAttribute.status.in_(['pending_next_chat', 'pending_current_chat']),
        )
        .order_by(models.UserAttribute.last_asked_at.asc().nulls_first())
    )
    pending_attrs = pending_res.all()
    
    # Busca perguntas snoozed que já expiraram
    snoozed_res = await db.execute(
        select(models.UserAttribute, models.AttributeDefinition)
        .join(models.AttributeDefinition, models.UserAttribute.attribute_definition_id == models.AttributeDefinition.id)
        .where(
            models.UserAttribute.user_id == user.id,
            models.UserAttribute.status == 'snoozed',
            models.UserAttribute.snooze_until <= now,
        )
        .order_by(models.UserAttribute.snooze_until.asc())
    )
    snoozed_attrs = snoozed_res.all()
    
    pending_list = []
    for ua, attr_def in pending_attrs:
        pending_list.append(schemas.PendingQuestion(
            attribute_code=attr_def.code,
            question_text=attr_def.label,
            helper_text=None,
            question_type=attr_def.attribute_type or 'text',
            status=ua.status,
            last_asked_at=ua.last_asked_at.isoformat() if ua.last_asked_at else None,
            snooze_until=ua.snooze_until.isoformat() if ua.snooze_until else None,
        ))
    
    for ua, attr_def in snoozed_attrs:
        pending_list.append(schemas.PendingQuestion(
            attribute_code=attr_def.code,
            question_text=attr_def.label,
            helper_text=None,
            question_type=attr_def.attribute_type or 'text',
            status=ua.status,
            last_asked_at=ua.last_asked_at.isoformat() if ua.last_asked_at else None,
            snooze_until=ua.snooze_until.isoformat() if ua.snooze_until else None,
        ))
    
    return schemas.PendingQuestionsResponse(
        pending=pending_list,
        total_pending=len(pending_list),
    )


@router.post("/pending/{attribute_code}/respond")
async def respond_pending(
    attribute_code: str,
    payload: schemas.OnboardingAnswer,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    User respondeu uma pergunta pendente (Sistema 2 — fora do onboarding).
    
    - Marca status como 'answered'
    - Atualiza profile.attributes
    - Retorna lista de próximas pendentes (se houver)
    """
    payload.attribute_code = attribute_code
    payload.action = 'answer'
    
    # Reusa a lógica do post_answer normal
    return await post_answer(payload, BackgroundTasks(), user, db)


@router.post("/pending/{attribute_code}/skip")
async def skip_pending(
    attribute_code: str,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    User pulou pergunta pendente no chat (Sistema 2).
    Avisa sobre limitação e pede confirmação.
    """
    attr_res = await db.execute(
        select(models.UserAttribute, models.AttributeDefinition)
        .join(models.AttributeDefinition, models.UserAttribute.attribute_definition_id == models.AttributeDefinition.id)
        .where(
            models.UserAttribute.user_id == user.id,
            models.AttributeDefinition.code == attribute_code,
        )
    )
    row = attr_res.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    
    ua, attr_def = row
    
    # Marca como 'pending_next_chat' (pergunta de novo no próximo chat)
    ua.status = 'pending_next_chat'
    ua.last_asked_at = datetime.utcnow()
    ua.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "attribute_code": attribute_code,
        "status": "pending_next_chat",
        "warning_message": (
            f"Sem problema! Mas saiba que sem essa informação, posso não te "
            f"interpretar tão bem. Quer continuar mesmo assim, ou prefere "
            f"responder depois?"
        ),
        "options": ["continue_without", "later"],
    }


@router.post("/pending/{attribute_code}/snooze")
async def snooze_pending(
    attribute_code: str,
    hours: int = 24,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Adia pergunta pendente por X horas"""
    attr_res = await db.execute(
        select(models.UserAttribute, models.AttributeDefinition)
        .join(models.AttributeDefinition, models.UserAttribute.attribute_definition_id == models.AttributeDefinition.id)
        .where(
            models.UserAttribute.user_id == user.id,
            models.AttributeDefinition.code == attribute_code,
        )
    )
    row = attr_res.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    
    ua, _ = row
    ua.status = 'snoozed'
    ua.snooze_until = datetime.utcnow() + timedelta(hours=hours)
    ua.last_asked_at = datetime.utcnow()
    ua.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "attribute_code": attribute_code,
        "status": "snoozed",
        "snooze_until": ua.snooze_until.isoformat(),
    }
