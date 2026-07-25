"""
Schemas admin: listagem, block, change password, role update, plan update, detalhes.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from ._base import uuid, datetime


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


class AdminUsersListResponse(BaseModel):
    """Resposta paginada do GET /api/admin/users (19/07/2026)."""
    items: List[AdminUserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserBlockRequest(BaseModel):
    """Request para bloquear/desbloquear user."""
    duration: str  # "1h", "24h", "permanent", "unblock"
    reason: Optional[str] = None


class AdminChangePasswordRequest(BaseModel):
    """Admin reseta senha de um user (não precisa da senha antiga)."""
    new_password: str
    reason: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    selected_plan_slug: Optional[str] = None
    # NÃO inclui role — promoção não permitida pela UI


class AdminRoleUpdate(BaseModel):
    """Troca role de um usuário. APENAS SUPER_ADMIN pode usar."""
    new_role: str  # 'user' | 'admin' | 'SUPER_ADMIN'
    reason: Optional[str] = None


class AdminPlanUpdate(BaseModel):
    """Admin edita um plano (nome, créditos, preço, ativo). NÃO muda slug."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    credits: Optional[int] = Field(default=None, ge=1, le=1000000)
    price_brl: Optional[float] = Field(default=None, ge=0, le=99999.99)
    active: Optional[bool] = None


# ============================================================
# DETALHES COMPLETOS DO USUÁRIO (admin)
# ============================================================
class AdminUserAttributeValue(BaseModel):
    """Valor de um atributo dinâmico atribuído ao user."""
    attribute_code: str
    attribute_name: str
    attribute_type: str
    value: Any


class AdminUserDetailResponse(AdminUserResponse):
    """Tudo sobre um usuário em uma única chamada — admin only."""
    profile_attributes: Optional[Dict[str, Any]] = None
    numerology_data: Optional[Dict[str, Any]] = None
    astrology_data: Optional[Dict[str, Any]] = None
    dynamic_attributes: List[AdminUserAttributeValue] = []
    chats_count: int = 0
    credit_transactions_count: int = 0
    last_chat_at: Optional[datetime] = None
    avatar_url: Optional[str] = None
    profile_status: Optional[str] = None
