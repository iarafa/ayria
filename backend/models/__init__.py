"""
AYRIA - SQLAlchemy Models (ORM)

Reflete o schema PostgreSQL definido em migrations/init.sql

REGRA: cada domínio mora em arquivo próprio.
- user.py        → User, UserProfile, UserAttribute
- onboarding.py  → OnboardingConfig, ChatQuestionSkip, SpiritualPreference
- attribute.py   → AttributeDefinition
- chat.py        → Chat, Message
- knowledge.py   → KnowledgeDocument
- audit.py       → AuditLog
- plan.py        → Plan
- credit.py      → CreditTransaction, AIUsageLog
- supervisor.py  → SupervisorAnalysis, SupervisorAlert, SupervisorDailySummary, UserSupervisorNote
- prompt.py      → AyriaPromptConfig, UserAlma
- system.py      → SystemConfig, ActionType
- stripe.py      → StripeSubscription, StripeInvoice, StripeWebhookEvent
- partner.py     → Partner, Coupon, CouponRedemption
- auth.py        → LoginLockout
"""
from database import Base

# User
from .user import User, UserProfile, UserAttribute

# Onboarding
from .onboarding import OnboardingConfig, ChatQuestionSkip, SpiritualPreference

# Attribute
from .attribute import AttributeDefinition

# Chat
from .chat import Chat, Message

# Knowledge
from .knowledge import KnowledgeDocument

# Audit
from .audit import AuditLog

# Plan
from .plan import Plan

# Credit
from .credit import CreditTransaction, AIUsageLog

# Supervisor
from .supervisor import (
    SupervisorAnalysis,
    SupervisorAlert,
    SupervisorDailySummary,
    UserSupervisorNote,
)

# Prompt
from .prompt import AyriaPromptConfig, UserAlma

# System
from .system import SystemConfig, ActionType

# Stripe
from .stripe_models import (
    StripeSubscription,
    StripeInvoice,
    StripeWebhookEvent,
)

# Partner
from .partner import Partner, Coupon, CouponRedemption

# Auth
from .auth import LoginLockout


__all__ = [
    "Base",
    # User
    "User", "UserProfile", "UserAttribute",
    # Onboarding
    "OnboardingConfig", "ChatQuestionSkip", "SpiritualPreference",
    # Attribute
    "AttributeDefinition",
    # Chat
    "Chat", "Message",
    # Knowledge
    "KnowledgeDocument",
    # Audit
    "AuditLog",
    # Plan
    "Plan",
    # Credit
    "CreditTransaction", "AIUsageLog",
    # Supervisor
    "SupervisorAnalysis", "SupervisorAlert", "SupervisorDailySummary", "UserSupervisorNote",
    # Prompt
    "AyriaPromptConfig", "UserAlma",
    # System
    "SystemConfig", "ActionType",
    # Stripe
    "StripeSubscription", "StripeInvoice", "StripeWebhookEvent",
    # Partner
    "Partner", "Coupon", "CouponRedemption",
    # Auth
    "LoginLockout",
]
