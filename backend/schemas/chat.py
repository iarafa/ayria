"""
Schemas de chat e mensagem.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from ._base import uuid, datetime


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
    action_type: Optional[str] = None  # slug do ActionType (ex: 'tarot', 'cartomancia')


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
    credit_balance: Optional[int] = None
    credit_consumed: Optional[int] = None
    credit_blocked: Optional[bool] = None

    class Config:
        from_attributes = True
