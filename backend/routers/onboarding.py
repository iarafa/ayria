"""
AYRIA - Onboarding Router
GET  /api/onboarding/status
POST /api/onboarding/answer
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime

from database import get_db
from utils.security import get_current_user
import models
import schemas

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.get("/status", response_model=schemas.OnboardingStatus)
async def get_status(
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna status + perguntas dinâmicas do onboarding"""
    # Carrega perfil
    profile_res = await db.execute(
        select(models.UserProfile).where(models.UserProfile.user_id == user.id)
    )
    profile = profile_res.scalar_one_or_none()
    
    # Carrega perguntas ativas
    questions_res = await db.execute(
        select(models.OnboardingConfig)
        .where(models.OnboardingConfig.is_active == True)
        .order_by(models.OnboardingConfig.step)
    )
    questions = questions_res.scalars().all()
    
    # Determina step atual
    answered = (profile.attributes or {}) if profile else {}
    current_step = len(answered) + 1
    
    return schemas.OnboardingStatus(
        status=user.onboarding_status or "pending",
        current_step=current_step,
        total_steps=len(questions),
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
    )


@router.post("/answer", response_model=schemas.UserResponse)
async def post_answer(
    payload: schemas.OnboardingAnswer,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Salva resposta de uma pergunta de onboarding"""
    profile_res = await db.execute(
        select(models.UserProfile).where(models.UserProfile.user_id == user.id)
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    
    # Salva resposta no JSONB
    attrs = dict(profile.attributes or {})
    if payload.attribute_code:
        attrs[payload.attribute_code] = payload.value
    profile.attributes = attrs
    
    # Atualiza status do user
    if user.onboarding_status == "pending":
        user.onboarding_status = "in_progress"
    
    # Se respondeu a última, marca como completed
    questions_count_res = await db.execute(
        select(func.count(models.OnboardingConfig.id))
        .where(models.OnboardingConfig.is_active == True)
    )
    total_questions = questions_count_res.scalar() or 0
    
    if len(attrs) >= total_questions:
        user.onboarding_status = "completed"
        profile.onboarding_completed = True
        
        # Dispara cálculo de numerologia (placeholder)
        user.numerology_data = calculate_numerology(attrs)
    
    await db.commit()
    await db.refresh(user)
    
    return schemas.UserResponse.model_validate(user)


def calculate_numerology(attrs: dict) -> dict:
    """
    Cálculo numerológico simplificado baseado nos dados de nascimento.
    Retorna mapa básico.
    """
    import re
    
    result = {}
    
    # Caminho de Vida (data de nascimento)
    data_nasc = attrs.get("data_nascimento", "")
    if data_nasc:
        nums = re.findall(r"\d+", data_nasc)
        if nums:
            soma = sum(int(n) for n in nums)
            while soma > 9 and soma not in (11, 22, 33):
                soma = sum(int(d) for d in str(soma))
            result["caminho_vida"] = soma
    
    # Expressão (nome completo)
    nome = attrs.get("nome_completo", "")
    if nome:
        valores = {
            'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6, 'g': 7, 'h': 8, 'i': 9,
            'j': 1, 'k': 2, 'l': 3, 'm': 4, 'n': 5, 'o': 6, 'p': 7, 'q': 8, 'r': 9,
            's': 1, 't': 2, 'u': 3, 'v': 4, 'w': 5, 'x': 6, 'y': 7, 'z': 8,
        }
        soma = sum(valores.get(c.lower(), 0) for c in nome if c.isalpha())
        while soma > 9 and soma not in (11, 22, 33):
            soma = sum(int(d) for d in str(soma))
        result["expressao"] = soma
    
    return result
