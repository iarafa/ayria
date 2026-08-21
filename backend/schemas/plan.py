"""
Schemas de planos comerciais.
"""
from typing import Optional
from pydantic import BaseModel

from ._base import uuid, datetime


class PlanResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    credits: int
    price_brl: float
    trial_days: Optional[int] = None  # NULL=plano normal, 7=trial
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True
