"""
Schemas de créditos: saldo, transações, ajustes admin.
"""
from typing import Optional, List
from pydantic import BaseModel

from ._base import uuid, datetime


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
