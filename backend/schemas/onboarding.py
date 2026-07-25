"""
Schemas de onboarding: perguntas, respostas, status, numerologia, perguntas pendentes.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from ._base import datetime


class OnboardingAnswer(BaseModel):
    question_step: int
    attribute_code: Optional[str] = None
    value: Optional[Any] = None
    # Ação do user no onboarding:
    # - 'answer' (default): responder a pergunta, salva o valor
    # - 'skip': pular, NÃO pergunta mais (status='skipped')
    # - 'later': responder depois, vai pra fila do Sistema 2 (status='pending_next_chat')
    # - 'continue_without': usuário confirmou que quer seguir sem esse dado (status='skipped')
    # - 'snooze': adiar por X horas (status='snoozed')
    action: Optional[str] = 'answer'
    snooze_hours: Optional[int] = 24


class OnboardingComplete(BaseModel):
    answers: List[OnboardingAnswer]


class OnboardingStatus(BaseModel):
    status: str  # pending|in_progress|completed
    current_step: int
    total_steps: int
    questions: List[Dict[str, Any]]
    numerology_data: Optional[Dict[str, Any]] = None
    answered: Optional[Dict[str, Any]] = None


class OnboardingAnswerResponse(BaseModel):
    status: str
    completed: bool
    numerology_data: Optional[Dict[str, Any]] = None
    numerology_calculated: bool = False
    progress: str  # ex: "3/9"
    profile_status: Optional[str] = "pending"
    warning_message: Optional[str] = None


class NumerologyResponse(BaseModel):
    mapa: Dict[str, Any]
    relatorio: str


# ============================================================
# SISTEMA 2 — Perguntas pendentes pra próximo chat
# ============================================================
class PendingQuestion(BaseModel):
    """Pergunta pendente pra perguntar no próximo chat novo"""
    attribute_code: str
    question_text: str
    helper_text: Optional[str] = None
    question_type: str
    status: str  # 'pending_next_chat' | 'pending_current_chat' | 'snoozed'
    last_asked_at: Optional[str] = None
    snooze_until: Optional[str] = None


class PendingQuestionsResponse(BaseModel):
    """Retorna todas as perguntas pendentes do user"""
    pending: List[PendingQuestion]
    total_pending: int


# ============================================================
# ADMIN - Onboarding Config
# ============================================================
class OnboardingConfigItem(BaseModel):
    step: int
    question_text: str
    helper_text: Optional[str] = None
    question_type: str
    attribute_code: Optional[str] = None
    options: Optional[List[Dict]] = None
    conditional_show: Optional[Dict] = None
