"""
Schemas de usuário: dados públicos, perfil, atualização.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel

from ._base import uuid, datetime


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
    billing_provider: Optional[str] = None
    external_customer_id: Optional[str] = None
    external_subscription_id: Optional[str] = None
    credits_last_granted_at: Optional[datetime] = None
    next_renewal_date: Optional[datetime] = None

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
