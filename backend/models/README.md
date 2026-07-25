# Pasta `backend/models/` — SQLAlchemy Models (ORM)

## O que mora aqui

Todos os SQLAlchemy models do banco de dados (ORM que reflete o schema PostgreSQL definido em `migrations/init.sql`).

## Regra

- **1 arquivo por domínio.** Não misturar domínios no mesmo arquivo.
- **NUNCA criar model novo em arquivo existente** — cria arquivo novo.
- Toda mudança aqui exige migration nova em `../migrations/`.
- Todo model precisa ter `__tablename__` explícito.
- UUIDs: usar `UUID(as_uuid=True)` como PK, default=`gen_uuid()`.
- Timestamps: usar `DateTime(timezone=True)` com `server_default=func.now()`.

## Estrutura

```
models/
├── README.md          # este arquivo
├── __init__.py        # importa e re-exporta todos os models (Alembic enxerga)
├── _base.py           # imports compartilhados + gen_uuid()
├── user.py            # User, UserProfile, UserAttribute
├── attribute.py       # AttributeDefinition (catálogo)
├── onboarding.py      # OnboardingConfig, ChatQuestionSkip, SpiritualPreference
├── chat.py            # Chat, Message
├── knowledge.py       # KnowledgeDocument
├── audit.py           # AuditLog
├── plan.py            # Plan (Básico/Intermediário/Premium)
├── credit.py          # CreditTransaction, AIUsageLog
├── supervisor.py      # SupervisorAnalysis, SupervisorAlert, SupervisorDailySummary, UserSupervisorNote
├── prompt.py          # AyriaPromptConfig (alma global), UserAlma (sub-alma individual)
├── system.py          # SystemConfig, ActionType
├── stripe_models.py   # StripeSubscription, StripeInvoice, StripeWebhookEvent
├── partner.py         # Partner, Coupon, CouponRedemption
└── auth.py            # LoginLockout
```

## Histórico de mudanças

- **2026-07-25** — DE quebrou `models.py` (764 linhas) em 14 arquivos por domínio. Comportamento idêntico, sem migrations novas.

## Pegadinhas conhecidas

- `User.email` é UNIQUE — não dá pra duplicar nem soft-delete.
- `Subscription` virou `StripeSubscription` (19/07/2026). Cuidado com imports antigos.
- `UserAlma.version` é UNIQUE por `(user_id, version)` — cada user tem várias versões históricas.
- `LoginLockout.identifier_type` aceita 'email' OU 'ip' — buscar pelos dois na hora de checar bloqueio.
- `Message.action_type_id` foi adicionado em 21/07/2026 (custo variável por tipo de ação).
- `User.avatar_url` é URL pública (Azure Blob) — não salvar base64 aqui.
- `SpiritualPreference` é 1:1 com User via PK compartilhada (`user_id` é PK e FK ao mesmo tempo).
- `AIUsageLog.chat_id` tem `ondelete="SET SET NULL"` (intencional? verificar se é typo de "SET NULL").
- `Partner.password_hash` (23/07/2026) — autenticação separada do AYRIA, no Portal do Parceiro.

## Como usar

```python
# import direto do módulo models (re-exporta tudo)
from models import User, Chat, Message

# ou import específico (recomendado em routers/services)
from models.user import User
from models.chat import Message
```

## Como adicionar model novo

1. Identifica o domínio → se já tem arquivo, **usa o existente**.
2. Se for domínio novo, cria arquivo novo + adiciona import em `__init__.py`.
3. Cria migration em `migrations/021_nome.sql`.
4. Atualiza este README (estrutura + pegadinhas).
