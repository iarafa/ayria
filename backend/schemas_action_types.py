"""
AYRIA — Action Types Schemas (21/07/2026)
Pydantic models pra CRUD de action_types via admin.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class ActionTypeBase(BaseModel):
    slug: str = Field(min_length=1, max_length=50, pattern=r"^[a-z_]+$")
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    credits_cost: int = Field(ge=1, le=100)
    is_special: bool = False
    category: str = "chat"
    icon: Optional[str] = None
    sort_order: int = 0
    active: bool = True


class ActionTypeCreate(ActionTypeBase):
    pass


class ActionTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    credits_cost: Optional[int] = Field(default=None, ge=1, le=100)
    is_special: Optional[bool] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    active: Optional[bool] = None


class ActionTypeResponse(ActionTypeBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True