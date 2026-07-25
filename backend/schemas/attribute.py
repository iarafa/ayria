"""
Schemas de AttributeDefinition (CRUD admin de catálogo de atributos dinâmicos).
"""
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from ._base import uuid, datetime


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
