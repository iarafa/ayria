"""
Schemas de planos comerciais.
"""
from pydantic import BaseModel

from ._base import uuid, datetime


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
