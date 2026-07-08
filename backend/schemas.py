"""
AYRIA - Pydantic Schemas
Validação de entrada/saída da API
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


# ============================================================
# AUTH
# ============================================================
class UserRegister(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)  # 🆕 min 8 chars (era 6)
    full_name: Optional[str] = None
    role: Optional[str] = "user"  # admin pode passar SUPER_ADMIN na criação
    plan_slug: Optional[str] = None  # basico|intermediario|premium — obrigatório em /auth/register (exceto admin criando user)


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None  # 🆕 7 dias, usado pra renovar
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


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str] = None
    role: str
    onboarding_status: str
    profile_status: Optional[str] = "pending"
    numerology_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None

    # Billing / Créditos
    selected_plan_id: Optional[uuid.UUID] = None
    selected_plan_slug: Optional[str] = None
    selected_plan_name: Optional[str] = None
    credit_balance: int = 0
    credit_status: str = "inactive"
    plan_selected_at: Optional[datetime] = None
    billing_status: str = "billing_not_enabled"
    credits_last_granted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# PLANS
# ============================================================
class PlanResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    credits: int
    price_brl: float
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# CREDITS
# ============================================================
class CreditBalanceResponse(BaseModel):
    """Saldo atual + plano + status"""
    selected_plan_id: Optional[uuid.UUID] = None
    selected_plan_slug: Optional[str] = None
    selected_plan_name: Optional[str] = None
    plan_price_brl: Optional[float] = None
    credit_balance: int
    credit_status: str
    plan_selected_at: Optional[datetime] = None
    billing_status: str
    credits_last_granted_at: Optional[datetime] = None


class CreditTransactionResponse(BaseModel):
    """Item do histórico de movimentações"""
    id: uuid.UUID
    type: str
    amount: int
    balance_before: int
    balance_after: int
    description: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CreditTransactionListResponse(BaseModel):
    """Lista paginada de transações"""
    items: List[CreditTransactionResponse]
    total: int
    page: int
    page_size: int


class CreditAdjustRequest(BaseModel):
    """Admin ajusta saldo de um user"""
    user_id: uuid.UUID
    amount: int  # positivo adiciona, negativo remove
    description: str  # motivo do ajuste
    type: Optional[str] = "adjustment_manual"  # bonus_manual | adjustment_manual | recharge_future | refund_future


# ============================================================
# PROFILE
# ============================================================
class ProfileUpdate(BaseModel):
    attributes: Dict[str, Any]


class ProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    attributes: Dict[str, Any]
    onboarding_completed: bool

    class Config:
        from_attributes = True


# ============================================================
# ONBOARDING
# ============================================================
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
    action: Optional[str] = 'answer'  # 'answer'|'skip'|'later'|'continue_without'|'snooze'
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
    profile_status: Optional[str] = "pending"  # pending|calculating|ready|failed
    # Mensagem de aviso quando user pula (sobre limitação de interpretação)
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
# CHATS & MESSAGES
# ============================================================
class ChatCreate(BaseModel):
    title: Optional[str] = None


class ChatUpdate(BaseModel):
    title: Optional[str] = None


class ChatResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: Optional[str]
    summary: Optional[str]
    created_at: datetime
    last_message_at: datetime
    message_count: Optional[int] = 0

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    chat_id: Optional[uuid.UUID] = None  # se None, cria novo chat
    content: str = Field(min_length=1, max_length=10000)


class MessageResponse(BaseModel):
    id: uuid.UUID
    chat_id: uuid.UUID
    role: str
    content: str
    ai_model: Optional[str]
    tokens_used: Optional[int]
    created_at: datetime
    metadata: Dict[str, Any] = {}
    # Créditos (consumidos se for user message + onboarding completo)
    credit_balance: Optional[int] = None       # saldo após processamento
    credit_consumed: Optional[int] = None      # créditos consumidos por esta mensagem
    credit_blocked: Optional[bool] = None      # True se saldo insuficiente

    class Config:
        from_attributes = True


# ============================================================
# ADMIN - Atributos
# ============================================================
class AttributeDefinitionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    label: str
    description: Optional[str] = None
    attribute_type: str  # text|date|select|...
    options: Optional[List[Dict]] = None
    is_required: bool = False
    is_onboarding: bool = True
    order_index: int = 0
    validation_rules: Optional[Dict] = None


class AttributeDefinitionResponse(AttributeDefinitionCreate):
    id: uuid.UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


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


# ============================================================
# ADMIN - Knowledge Documents
# ============================================================
class KnowledgeDocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    file_name: Optional[str]
    file_size_bytes: Optional[int]
    storage_url: Optional[str] = None
    storage_provider: Optional[str] = None
    status: str
    chunks_count: int
    indexed_at: Optional[datetime]
    collection: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# ADMIN - Users
# ============================================================
class AdminUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    onboarding_status: str
    created_at: datetime
    last_login_at: Optional[datetime]
    message_count: int = 0

    # Billing / Créditos
    selected_plan_id: Optional[uuid.UUID] = None
    selected_plan_slug: Optional[str] = None
    selected_plan_name: Optional[str] = None
    credit_balance: int = 0
    credit_status: str = "inactive"
    plan_selected_at: Optional[datetime] = None
    billing_status: str = "billing_not_enabled"
    credits_last_granted_at: Optional[datetime] = None

    # Block
    blocked_until: Optional[datetime] = None
    blocked_at: Optional[datetime] = None
    blocked_by: Optional[uuid.UUID] = None
    block_reason: Optional[str] = None

    class Config:
        from_attributes = True


class UserBlockRequest(BaseModel):
    """Request para bloquear/desbloquear user."""
    duration: str  # "1h", "24h", "permanent", "unblock"
    reason: Optional[str] = None


class AdminChangePasswordRequest(BaseModel):
    """Admin reseta senha de um user (não precisa da senha antiga).
    Auditoria: loga quem mudou + motivo opcional.
    """
    new_password: str  # min 8 (validado no endpoint)
    reason: Optional[str] = None  # motivo da troca (auditoria)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    selected_plan_slug: Optional[str] = None  # admin pode trocar plano do user (gera transaction)
    # NÃO inclui role — promoção não permitida pela UI


class AdminPlanUpdate(BaseModel):
    """Admin edita um plano (nome, créditos, preço, ativo). NÃO muda slug (identidade)."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    credits: Optional[int] = Field(default=None, ge=1, le=1000000)
    price_brl: Optional[float] = Field(default=None, ge=0, le=99999.99)
    active: Optional[bool] = None


# ============================================================
# DETALHES COMPLETOS DO USUÁRIO (admin)
# ============================================================
class AdminUserAttributeValue(BaseModel):
    """Valor de um atributo dinâmico atribuído ao user."""
    attribute_code: str  # ex: 'cor_favorita', 'profissao'
    attribute_name: str  # ex: 'Cor favorita', 'Profissão'
    attribute_type: str  # ex: 'text', 'select', 'multiselect'
    value: Any  # json (string, number, list, etc)


class AdminUserDetailResponse(AdminUserResponse):
    """Tudo sobre um usuário em uma única chamada — admin only.
    
    Inclui dados básicos + plano + saldo + profile_attributes (dados crus do onboarding)
    + numerology_data + astrology_data + atributos dinâmicos + stats de uso.
    """
    # Dados crus do onboarding (preenchidos pelo user)
    profile_attributes: Optional[Dict[str, Any]] = None  # user_profiles.attributes (jsonb)
    
    # Dados calculados (gerados pelo backend)
    numerology_data: Optional[Dict[str, Any]] = None  # users.numerology_data (jsonb)
    astrology_data: Optional[Dict[str, Any]] = None  # users.astrology_data (jsonb)
    
    # Atributos dinâmicos atribuídos pelo admin (via attribute_definitions)
    dynamic_attributes: List[AdminUserAttributeValue] = []
    
    # Stats de uso
    chats_count: int = 0
    credit_transactions_count: int = 0
    last_chat_at: Optional[datetime] = None
    
    # Avatar
    avatar_url: Optional[str] = None
    profile_status: Optional[str] = None


# Update forward refs
TokenResponse.model_rebuild()


# ============================================================
# SPIRITUAL PREFERENCES (Sistema 5)
# ============================================================
RELIGION_OPTIONS = [
    # Chave, Label, Emoji
    ("prefiro_nao_dizer",   "Prefiro não dizer",     "🤐"),
    ("ateu",                "Ateu / Ateísta",        "🧠"),
    ("agnostico",           "Agnóstico",             "🤔"),
    ("cristao_catolico",    "Cristianismo (Católico)", "✝️"),
    ("cristao_evangelico",  "Cristianismo (Evangélico)", "📖"),
    ("cristao_ortodoxo",    "Cristianismo (Ortodoxo)",   "☦️"),
    ("espirita_kardecista", "Espírita (Kardecista)", "📚"),
    ("espirita_livre",      "Espírita Livre",        "✨"),
    ("umbanda",             "Umbanda",               "🪘"),
    ("candomble",           "Candomblé",             "🥁"),
    ("santo_daime",         "Santo Daime / Ayahuasca","🌿"),
    ("judaísmo",            "Judaísmo",              "🕎"),
    ("islamismo",           "Islamismo",             "☪️"),
    ("budismo",             "Budismo",               "☸️"),
    ("hinduismo",           "Hinduísmo",             "🕉️"),
    ("testemunha_jeova",    "Testemunha de Jeová",   "🏛️"),
    ("espiritualista",      "Espiritualista / Messiânico", "🔮"),
    ("tradicao_indigena",   "Tradições Indígenas BR","🌎"),
    ("budista_secular",     "Budista Secular",       "🧘"),
    ("outro",               "Outra (descrever)",     "✏️"),
]


class SpiritualPreferenceResponse(BaseModel):
    user_id: uuid.UUID
    religion: str
    religion_label: Optional[str] = None   # preenchido pelo backend pra ficar UI-friendly
    religion_emoji: Optional[str] = None
    custom_label: Optional[str] = None
    custom_tags: List[str] = []
    notes: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SpiritualPreferenceUpdate(BaseModel):
    religion: str                          # uma das RELIGION_OPTIONS
    custom_label: Optional[str] = None    # obrigatório se religion='outro'
    custom_tags: List[str] = []
    notes: Optional[str] = None
    is_active: bool = True


class ReligionOption(BaseModel):
    value: str
    label: str
    emoji: str


class ReligionOptionsResponse(BaseModel):
    options: List[ReligionOption]
