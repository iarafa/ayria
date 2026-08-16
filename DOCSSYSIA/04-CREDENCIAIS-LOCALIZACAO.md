# Localização das credenciais (SEM expor valores)

⚠️ **NUNCA** commitar `.env` no git. SEMPRE em `/etc/ayria/` com perm 600.

## VPS — arquivos de credenciais

| Arquivo | Permissões | Conteúdo |
|---|---|---|
| `/etc/ayria/.env` | 600 root:ayria-app | POSTGRES_PASSWORD, JWT_SECRET, AI_API_KEY, STRIPE_*, TURBOSMTP_*, MAIL_FROM, AZURE_STORAGE_SAS_URL, etc. |
| `/etc/ayria/.env-staging` | 600 root:ayria-app | Mesmas vars, mas BACKEND_PORT=8001, ENVIRONMENT=staging |
| `/opt/ayria/backend/.env` | 640 ayria-app:ayria-app | Cópia de `/etc/ayria/.env` (pydantic-settings lê do CWD) |
| `/etc/ssl/ayria/cert.pem` | 644 | Cert TLS auto-assinado |
| `/etc/ssl/ayria/key.pem` | 640 caddy:caddy | Chave privada TLS |

## VPS — variáveis de ambiente por categoria

### Banco (PostgreSQL)
- **POSTGRES_USER**: ayria
- **POSTGRES_PASSWORD**: (em `/etc/ayria/.env`)
- **POSTGRES_DB**: ayria
- **DATABASE_URL**: `postgresql+asyncpg://ayria:***@127.0.0.1:5432/ayria`

### JWT
- **JWT_SECRET**: gerado por `openssl rand -hex 32` (em `/etc/ayria/.env`)

### IA (MiniMax — REGRA ABSOLUTA, NUNCA OpenAI)
- **AI_API_KEY**: sk-cp-POEsU... (em `/etc/ayria/.env`)
- **AI_BASE_URL**: https://api.minimax.io/v1
- **AI_MODEL**: MiniMax-M3

### Azure Blob Storage
- **AZURE_STORAGE_SAS_URL**: https://replitapp01.blob.core.windows.net/ayria?... (em `/etc/ayria/.env`)
- **AZURE_STORAGE_CONTAINER**: ayria

### TurboSMTP (email)
- **TURBOSMTP_CONSUMER_KEY**: c10e79846c... (em `/etc/ayria/.env`)
- **TURBOSMTP_CONSUMER_SECRET**: m802S1ZJxY... (em `/etc/ayria/.env`)
- **MAIL_FROM**: ayria@tecia.app

### Stripe (TEST MODE — não fazer transações reais)
- **STRIPE_SECRET_KEY**: sk_test_51SFcEC... (em `/etc/ayria/.env`)
- **STRIPE_PUBLISHABLE_KEY**: pk_test_51SFcEC... (em `/etc/ayria/.env`)
- **STRIPE_WEBHOOK_SECRET**: whsec_683e52e9... (em `/etc/ayria/.env`)
- **STRIPE_PRICE_BASIC**: price_1Tv1xsEBAKrKd7TmmSKCUasj
- **STRIPE_PRICE_PREMIUM**: price_1Tv1yvEBAKrKd7TmIRAuhN1O
- **STRIPE_PRICE_GOLD**: price_1Tv1zHEBAKrKd7TmiTNwjdwW
- **STRIPE_TRIAL_CREDITS**: 10

### SSH (acesso à VPS)
- **Porta**: 2222 (NÃO 22)
- **Chave privada (local)**: `~/.ssh/ayria-prod-DE-ed25519`
- **User**: root

## Local — variáveis locais

| Item | Onde |
|---|---|
| Token Telegram `@de_peron_bot` | `/home/peron/.openclaw/workspace/TOOLS.md` (Azure section) |
| Token Telegram `@avisos_perontec_bot` | `/home/peron/.telegram_bots.env` (AVISOS_TOKEN) | ⚠️ NÃO MAIS USADO PELO AYRIA (16/08/2026) — token consolidado em `/etc/ayria/.env` |
| GitHub PAT pessoal (iarafa) | `/home/peron/.openclaw/workspace/TOOLS.md` |
| Memória de longo prazo | `/home/peron/.openclaw/workspace/MEMORY.md` |
| Diário diário | `/home/peron/.openclaw/workspace/memory/YYYY-MM-DD.md` |
| Vault Obsidian (referência) | `~/Área de trabalho/OBSIDIANDATA/PERON/` |

## Como ROTACIONAR uma credencial

1. Gerar nova credencial no provedor (Stripe, TurboSMTP, etc)
2. Editar `/etc/ayria/.env` na VPS: `vim /etc/ayria/.env`
3. Editar também `/etc/ayria/.env-staging` (se aplicável)
4. **Copiar pra `/opt/ayria/backend/.env`** (pydantic-settings lê do CWD):
   ```bash
   cp /etc/ayria/.env /opt/ayria/backend/.env
   chown ayria-app:ayria-app /opt/ayria/backend/.env
   chmod 640 /opt/ayria/backend/.env
   ```
5. Restart do backend:
   ```bash
   systemctl restart ayria-backend && systemctl restart ayria-backend-staging
   ```
6. Validar que pegou:
   ```bash
   PID=$(pgrep -f 'uvicorn main:app' | head -1)
   sudo -u ayria-app cat /proc/$PID/environ | tr '\0' '\n' | grep -i NOME_DA_VAR
   ```
