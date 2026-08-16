# Arquitetura AYRIA em produção (14/08/2026)

## Diagrama de fluxo

```
[Usuário] ──HTTPS──> [Cloudflare proxy ON] ──HTTPS──> [VPS :443]
                                                          │
                                                          ▼
                                                    [Caddy]
                                                          │
                                       ┌──────────────────┼──────────────────┐
                                       ▼                                     ▼
                          [/api/*, /health, /docs]                  [/ (outros)]
                                       │                                     │
                                       ▼                                     ▼
                          [uvicorn :8000 prod]                    [file_server]
                          [uvicorn :8001 staging]                 /opt/ayria/frontend/dist
                                       │                                     │
                          ┌────────────┼────────────┐                        │
                          ▼            ▼            ▼                        │
                    [PostgreSQL]  [Qdrant]   [Azure Blob]              [SPA React]
                    :5432         :6333      (SAS URL)                 (HashRouter)
                          │
                          └─ 32 tabelas, 36 users (restaurado do local)
```

## Stack completa

| Camada | Tecnologia | Versão | Como roda |
|---|---|---|---|
| OS | Ubuntu | 26.04 LTS | Nativo |
| Web server | Caddy | 2.6.2 | systemd `caddy.service` |
| Reverse proxy | Caddy (mesmo) | — | `reverse_proxy` no Caddyfile |
| TLS termination | Caddy | — | Cert auto-assinado (SAN: ayria.online, www, teste) |
| Backend prod | uvicorn + FastAPI | uvicorn 0.32.0 | systemd `ayria-backend.service`, user `ayria-app` |
| Backend staging | uvicorn + FastAPI | mesmo | systemd `ayria-backend-staging.service`, :8001 |
| Banco | PostgreSQL | 18.4 (nativo, mesma versão do local AYRIA) | apt postgresql-18 + pgdg repo |
| Vector DB | Qdrant | 1.12.4 | binário standalone em `/opt/qdrant/qdrant` |
| Frontend | Vite + React | Vite 5.4.21, React 18 | build em `/opt/ayria/frontend/dist/` |
| DNS | Cloudflare | — | Proxy ON para ambos subdomínios |
| Email | TurboSMTP | API v2 | via `email_turbo.py` |
| Pagamento | Stripe | API + webhooks | test mode (sk_test_...) |
| AI | MiniMax | MiniMax-M3 | via OpenAI-compatible client |
| Storage | Azure Blob | — | via SAS URL |

## Ports mapping

```
Internet (HTTPS:443)
  └─> Cloudflare proxy
       └─> VPS :443 (Caddy TLS termination)
            ├─> :80 (redirect to HTTPS)
            ├─> /api/*, /health, /docs → 127.0.0.1:8000 (prod) ou :8001 (staging)
            └─> / (outros) → /opt/ayria/frontend/dist/* (SPA)

VPS internal:
  - 127.0.0.1:5432  → PostgreSQL (ayria user, database `ayria`)
  - 127.0.0.1:6333  → Qdrant HTTP (porta fechada externamente)
  - 127.0.0.1:6334  → Qdrant gRPC (porta fechada externamente)
  - 127.0.0.1:8000  → uvicorn prod
  - 127.0.0.1:8001  → uvicorn staging

SSH:
  - Porta 2222 (NÃO 22) — chave `~/.ssh/ayria-prod-DE-ed25519`
```

## Paths importantes na VPS

```
/opt/ayria/                          # código AYRIA (git clone)
├── .venv/                           # Python 3.12 venv
├── backend/                         # FastAPI source
│   ├── .env                         # pydantic-settings lê (cópia de /etc/ayria/.env)
│   └── routers/                     # endpoints
├── frontend/
│   └── dist/                        # build Vite (servido pelo Caddy)
├── DOCSSYSIA/                       # esta documentação
└── (git: feature/sub-alma-user branch)

/etc/ayria/                          # credenciais (perms 600 root:ayria-app)
├── .env                             # prod env vars
└── .env-staging                     # staging env vars (BACKEND_PORT=8001)

/etc/caddy/Caddyfile                 # config Caddy (vhosts ayria.online + teste.ayria.online)
/etc/ssl/ayria/                      # cert auto-assinado (SAN: ayria, www, teste)
/etc/systemd/system/
├── caddy.service
├── ayria-backend.service
└── ayria-backend-staging.service

/var/log/
├── caddy/ayria.log                  # log Caddy prod
├── caddy/staging.log                # log Caddy staging
└── ayria/                           # log uvicorn prod (AYRIA_LOG_DIR)

/opt/qdrant/
├── qdrant                           # binário
└── start.sh                         # script start (atualmente rodando via nohup)

/home/peron/.openclaw/workspace/DOCSSYSIA/  # esta pasta (local)
```

## Banco de dados — schema resumido

**32 tabelas** no schema `public` do banco `ayria`. Principais:

- `users` — 36 usuários
- `chats` / `messages` — conversas
- `user_profiles` / `user_alma` / `user_attributes`
- `plans` (3: basico, intermediario, premium)
- `stripe_subscriptions` / `stripe_invoices` / `stripe_webhook_events`
- `coupons` / `coupon_redemptions`
- `partners`
- `audit_log` (8k+ registros)
- `credit_transactions` (251)
- `ai_usage_log`
- `schema_migrations` (24 migrations aplicadas)
