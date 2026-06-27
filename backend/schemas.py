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
    password: str = Field(min_length=6, max_length=128)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    role: str
    onboarding_status: str
    numerology_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


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
    value: Any


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


class NumerologyResponse(BaseModel):
    mapa: Dict[str, Any]
    relatorio: str


# ============================================================
# CHATS & MESSAGES
# ============================================================
class ChatCreate(BaseModel):
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

    class Config:
        from_attributes = True


class UserRoleUpdate(BaseModel):
    role: str = Field(pattern=r"^(user|admin|SUPER_ADMIN)$")


# Update forward refs
TokenResponse.model_rebuild()
