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
from datetime import datetime
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

    # Carrega perguntas ativas
    questions_res = await db.execute(
        select(models.OnboardingConfig)
        .where(models.OnboardingConfig.is_active == True)
        .order_by(models.OnboardingConfig.step)
    )
    questions = questions_res.scalars().all()

    # Step atual = quantas respostas já tem + 1
    current_step = len(answered_attrs) + 1

    return schemas.OnboardingStatus(
        status=user.onboarding_status or "pending",
        current_step=current_step,
        total_steps=len(questions),
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
    
    - Salva em user_attributes (tabela)
    - Atualiza profile.attributes (JSONB para compatibilidade)
    - Se última pergunta → calcula numerologia e marca completed
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
    if existing:
        existing.value = payload.value
        existing.updated_at = datetime.utcnow()
    else:
        new_attr = models.UserAttribute(
            id=uuid.uuid4(),
            user_id=user.id,
            attribute_definition_id=attr_def.id,
            value=payload.value,
        )
        db.add(new_attr)

    # 2. Sincroniza em profile.attributes (JSONB para retrocompat)
    attrs_jsonb = dict(profile.attributes or {})
    attrs_jsonb[payload.attribute_code] = payload.value
    profile.attributes = attrs_jsonb

    # 3. Atualiza status
    if user.onboarding_status == "pending":
        user.onboarding_status = "in_progress"

    # 4. Verifica se completou TODAS perguntas
    total_questions_res = await db.execute(
        select(func.count(models.OnboardingConfig.id))
        .where(models.OnboardingConfig.is_active == True)
    )
    total_questions = total_questions_res.scalar() or 0

    answered_count_res = await db.execute(
        select(func.count(models.UserAttribute.id))
        .where(models.UserAttribute.user_id == user.id)
    )
    answered_count = answered_count_res.scalar() or 0

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
