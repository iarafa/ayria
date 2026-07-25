"""
Schemas de Partner, Coupon, Redemption, Commission.
"""
from typing import Optional, List
from pydantic import BaseModel


class PartnerCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    pix_key: Optional[str] = None
    commission_pct: Optional[float] = None
    notes: Optional[str] = None


class PartnerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    pix_key: Optional[str] = None
    commission_pct: Optional[float] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


class PartnerResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    pix_key: Optional[str] = None
    commission_pct: Optional[float] = None
    notes: Optional[str] = None
    active: bool
    created_at: str
    coupons_count: int = 0
    total_commission_cents: int = 0

    class Config:
        from_attributes = True


class CouponCreate(BaseModel):
    code: str
    name: Optional[str] = None
    partner_id: Optional[str] = None
    discount_type: str  # 'percent' | 'fixed'
    discount_value: float
    applicable_plan_slug: str
    duration_months: int = 1
    commission_pct: float
    max_redemptions: Optional[int] = None
    expires_at: Optional[str] = None


class CouponUpdate(BaseModel):
    name: Optional[str] = None
    commission_pct: Optional[float] = None
    max_redemptions: Optional[int] = None
    expires_at: Optional[str] = None
    active: Optional[bool] = None


class CouponResponse(BaseModel):
    id: str
    code: str
    stripe_coupon_id: str
    partner_id: Optional[str] = None
    partner_name: Optional[str] = None
    name: Optional[str] = None
    discount_type: str
    discount_value: float
    applicable_plan_slug: str
    duration_months: int
    commission_pct: float
    max_redemptions: Optional[int] = None
    current_redemptions: int
    expires_at: Optional[str] = None
    active: bool
    created_at: str

    class Config:
        from_attributes = True


class CouponValidateRequest(BaseModel):
    code: str
    plan_slug: Optional[str] = None


class CouponValidateResponse(BaseModel):
    valid: bool
    coupon_id: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    applicable_plan_slug: Optional[str] = None
    duration_months: Optional[int] = None
    partner_name: Optional[str] = None
    preview: Optional[dict] = None
    error: Optional[str] = None


class RedemptionResponse(BaseModel):
    id: str
    coupon_code: Optional[str] = None
    partner_name: Optional[str] = None
    user_email: Optional[str] = None
    plan_slug: str
    original_amount_cents: int
    discount_amount_cents: int
    final_amount_cents: int
    commission_pct: Optional[float] = None
    commission_amount_cents: Optional[int] = None
    payout_status: str
    payout_at: Optional[str] = None
    created_at: str


class CommissionReportResponse(BaseModel):
    items: list
    total_pending_cents: int
    total_paid_cents: int
    period_start: Optional[str] = None
    period_end: Optional[str] = None
