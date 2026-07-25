"""
AYRIA - Pydantic Schemas

Validação de entrada/saída da API, separado por domínio.

REGRA: cada domínio mora em arquivo próprio.
- auth.py        → registro, login, tokens, verificação email
- user.py        → perfil do user, dados públicos
- plan.py        → planos comerciais
- credit.py      → saldo, transações, ajustes admin
- onboarding.py  → onboarding (perguntas, respostas, status, numerologia)
- chat.py        → chats e mensagens
- attribute.py   → AttributeDefinition (CRUD admin)
- knowledge.py   → KnowledgeDocument
- admin.py       → operações admin (block user, change password, role update, etc)
- spiritual.py   → preferência religiosa + RELIGION_OPTIONS
- ratelimit.py   → dashboard de rate limit + blacklist
- partner.py     → Partner, Coupon, Redemption, Commission
- lockout.py     → LoginLockout admin
"""
from .auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RegisterResponse,
    VerifyEmailResponse,
    ResendVerificationResponse,
)
from .user import UserResponse, ProfileUpdate, ProfileResponse
from .plan import PlanResponse
from .credit import (
    CreditBalanceResponse,
    CreditTransactionResponse,
    CreditTransactionListResponse,
    CreditAdjustRequest,
)
from .onboarding import (
    OnboardingAnswer,
    OnboardingComplete,
    OnboardingStatus,
    OnboardingAnswerResponse,
    NumerologyResponse,
    PendingQuestion,
    PendingQuestionsResponse,
    OnboardingConfigItem,
)
from .chat import (
    ChatCreate,
    ChatUpdate,
    ChatResponse,
    MessageCreate,
    MessageResponse,
)
from .attribute import (
    AttributeDefinitionCreate,
    AttributeDefinitionResponse,
)
from .knowledge import KnowledgeDocumentResponse
from .admin import (
    AdminUserResponse,
    AdminUsersListResponse,
    UserBlockRequest,
    AdminChangePasswordRequest,
    UserUpdate,
    AdminRoleUpdate,
    AdminPlanUpdate,
    AdminUserAttributeValue,
    AdminUserDetailResponse,
)
from .spiritual import (
    RELIGION_OPTIONS,
    SpiritualPreferenceResponse,
    SpiritualPreferenceUpdate,
    ReligionOption,
    ReligionOptionsResponse,
)
from .ratelimit import (
    RateLimitStatusResponse,
    RateLimitBlockedIP,
    RateLimitAlertIP,
    RateLimitEventsPage,
    RateLimitBlockedList,
    RateLimitAlertList,
    BlacklistItem,
    BlacklistAddRequest,
    BlacklistResponse,
    RateLimitUnblockRequest,
    RateLimitConfigResponse,
    RateLimitToggleRequest,
)
from .partner import (
    PartnerCreate,
    PartnerUpdate,
    PartnerResponse,
    CouponCreate,
    CouponUpdate,
    CouponResponse,
    CouponValidateRequest,
    CouponValidateResponse,
    RedemptionResponse,
    CommissionReportResponse,
)
from .lockout import LoginLockoutInfo, LoginLockoutUnlockRequest


# Resolver forward refs do TokenResponse (referencia UserResponse)
TokenResponse.model_rebuild()


__all__ = [
    # auth
    "UserRegister", "UserLogin", "TokenResponse", "RegisterResponse",
    "VerifyEmailResponse", "ResendVerificationResponse",
    # user
    "UserResponse", "ProfileUpdate", "ProfileResponse",
    # plan
    "PlanResponse",
    # credit
    "CreditBalanceResponse", "CreditTransactionResponse",
    "CreditTransactionListResponse", "CreditAdjustRequest",
    # onboarding
    "OnboardingAnswer", "OnboardingComplete", "OnboardingStatus",
    "OnboardingAnswerResponse", "NumerologyResponse",
    "PendingQuestion", "PendingQuestionsResponse", "OnboardingConfigItem",
    # chat
    "ChatCreate", "ChatUpdate", "ChatResponse", "MessageCreate", "MessageResponse",
    # attribute
    "AttributeDefinitionCreate", "AttributeDefinitionResponse",
    # knowledge
    "KnowledgeDocumentResponse",
    # admin
    "AdminUserResponse", "AdminUsersListResponse", "UserBlockRequest",
    "AdminChangePasswordRequest", "UserUpdate", "AdminRoleUpdate",
    "AdminPlanUpdate", "AdminUserAttributeValue", "AdminUserDetailResponse",
    # spiritual
    "RELIGION_OPTIONS", "SpiritualPreferenceResponse", "SpiritualPreferenceUpdate",
    "ReligionOption", "ReligionOptionsResponse",
    # ratelimit
    "RateLimitStatusResponse", "RateLimitBlockedIP", "RateLimitAlertIP",
    "RateLimitEventsPage", "RateLimitBlockedList", "RateLimitAlertList",
    "BlacklistItem", "BlacklistAddRequest", "BlacklistResponse",
    "RateLimitUnblockRequest", "RateLimitConfigResponse", "RateLimitToggleRequest",
    # partner
    "PartnerCreate", "PartnerUpdate", "PartnerResponse",
    "CouponCreate", "CouponUpdate", "CouponResponse",
    "CouponValidateRequest", "CouponValidateResponse",
    "RedemptionResponse", "CommissionReportResponse",
    # lockout
    "LoginLockoutInfo", "LoginLockoutUnlockRequest",
]
