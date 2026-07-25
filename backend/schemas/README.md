# Pasta `backend/schemas/` — Pydantic Schemas (DTOs)

## O que mora aqui

Todos os schemas Pydantic de validação entrada/saída da API.

## Regra

- **1 arquivo por domínio.** Não misturar domínios no mesmo arquivo.
- **NUNCA criar schema novo em arquivo existente** — cria arquivo novo.
- `model_rebuild()` só é chamado em `__init__.py` (forward refs ficam centralizadas lá).
- Todo schema novo que mexer em response precisa ter `class Config: from_attributes = True`.

## Estrutura

```
schemas/
├── README.md          # este arquivo
├── __init__.py        # re-exporta todos (compat com `from schemas import X`)
├── _base.py           # imports compartilhados (pydantic, typing, datetime, uuid)
├── auth.py            # UserRegister, UserLogin, TokenResponse, RegisterResponse, VerifyEmailResponse, ResendVerificationResponse
├── user.py            # UserResponse, ProfileUpdate, ProfileResponse
├── plan.py            # PlanResponse
├── credit.py          # CreditBalanceResponse, CreditTransactionResponse, CreditTransactionListResponse, CreditAdjustRequest
├── onboarding.py      # OnboardingAnswer, OnboardingComplete, OnboardingStatus, OnboardingAnswerResponse, NumerologyResponse, PendingQuestion, PendingQuestionsResponse, OnboardingConfigItem
├── chat.py            # ChatCreate, ChatUpdate, ChatResponse, MessageCreate, MessageResponse
├── attribute.py       # AttributeDefinitionCreate, AttributeDefinitionResponse
├── knowledge.py       # KnowledgeDocumentResponse
├── admin.py           # AdminUserResponse, AdminUsersListResponse, UserBlockRequest, AdminChangePasswordRequest, UserUpdate, AdminRoleUpdate, AdminPlanUpdate, AdminUserAttributeValue, AdminUserDetailResponse
├── spiritual.py       # RELIGION_OPTIONS, SpiritualPreferenceResponse, SpiritualPreferenceUpdate, ReligionOption, ReligionOptionsResponse
├── ratelimit.py       # RateLimitStatusResponse, RateLimitBlockedIP, ..., RateLimitToggleRequest, Blacklist*
├── partner.py         # Partner*, Coupon*, RedemptionResponse, CommissionReportResponse
└── lockout.py         # LoginLockoutInfo, LoginLockoutUnlockRequest
```

## Histórico de mudanças

- **2026-07-25** — DE quebrou `schemas.py` (765 linhas, 65 schemas) em 13 arquivos por domínio. Comportamento idêntico.

## Pegadinhas conhecidas

- `TokenResponse.user` é forward ref pro `UserResponse` — `model_rebuild()` é chamado em `__init__.py`.
- `RELIGION_OPTIONS` é constante (lista de tuplas) — importada como lista, não como enum.
- `MessageResponse.metadata` é `Dict[str, Any]` mesmo (frontend envia JSON livre).
- `MessageCreate.action_type` é slug do ActionType (21/07/2026) — string, não FK.
- `CreditTransactionResponse` usa `class Config: from_attributes = True` pra serializar do ORM.
- `AdminUserDetailResponse(AdminUserResponse)` herda todos os campos + adiciona profile_attributes/numerology/astrology/dynamic_attributes/stats.
- `RateLimit*` schemas ficam em arquivo único (12 schemas correlatos, melhor deixar juntos).
- `PartnerResponse.id` é `str` (não UUID) — `from_attributes=True` lê string do ORM por causa de algum path que converte.
- `CommissionReportResponse.items` é `list` puro (não tipado) — conteúdo varia por filtros.

## Como usar

```python
# import direto do módulo schemas (re-exporta tudo)
from schemas import UserRegister, TokenResponse

# ou import específico (recomendado)
from schemas.auth import UserRegister
from schemas.chat import MessageCreate
```

## Compatibilidade

`from schemas import X` continua funcionando pra TODOS os schemas — `__init__.py` re-exporta. Códigos antigos não quebram.
